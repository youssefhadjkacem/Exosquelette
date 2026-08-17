"""Run unassisted, passive and hybrid closed-loop trajectory tracking in MuJoCo."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import mujoco
import numpy as np


SRC_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline_utils import dump_json, resolve_project_path, write_csv_rows  # noqa: E402
from evaluate_classical_assistance import metrics, read_mot  # noqa: E402


def target_kinematics(columns: list[str], motion: np.ndarray, joint_names: list[str]):
    times = motion[:, 0]
    qpos = np.column_stack([np.radians(motion[:, columns.index(name)]) for name in joint_names])
    qvel = np.gradient(qpos, times, axis=0)
    qacc = np.gradient(qvel, times, axis=0)
    return times, qpos, qvel, qacc


def interpolate(time_s: float, times: np.ndarray, values: np.ndarray) -> np.ndarray:
    return np.asarray([np.interp(time_s, times, values[:, index]) for index in range(values.shape[1])])


def disable_muscles(model: mujoco.MjModel) -> list[int]:
    exo_indices, muscle_indices = [], []
    for index in range(model.nu):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, index) or ""
        if name.startswith("exo_"):
            exo_indices.append(index)
        else:
            muscle_indices.append(index)
    if muscle_indices:
        model.actuator_gainprm[muscle_indices] = 0.0
        model.actuator_biasprm[muscle_indices] = 0.0
    return exo_indices


def simulate(condition: str, model_path: Path, config: dict, columns: list[str], motion: np.ndarray):
    model = mujoco.MjModel.from_xml_path(str(model_path))
    joint_names = [
        mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, index) for index in range(model.njnt)
    ]
    if model.nq != model.nv or model.nq != len(joint_names):
        raise ValueError("Le controleur V1 exige uniquement des articulations scalaires.")
    if config["simulation"]["disable_all_contacts"]:
        model.geom_contype[:] = 0
        model.geom_conaffinity[:] = 0
    exo_indices = disable_muscles(model) if config["simulation"]["disable_muscle_actuators"] else []
    times, target_qpos, target_qvel, target_qacc = target_kinematics(columns, motion, joint_names)
    data = mujoco.MjData(model)
    data.qpos[:] = target_qpos[0]
    data.qvel[:] = target_qvel[0]
    mujoco.mj_forward(model, data)

    kp = np.asarray([config["tracking_gains"][name]["kp"] for name in joint_names], dtype=float)
    kd = np.asarray([config["tracking_gains"][name]["kd"] for name in joint_names], dtype=float)
    human_limits = np.asarray([config["human_torque_limits_nm"][name] for name in joint_names], dtype=float)
    assistance = np.asarray([
        config["hybrid_assistance_fraction"].get(name, 0.0) if condition == "hybrid" else 0.0
        for name in joint_names
    ])
    motor_index_by_joint = {}
    if condition == "hybrid":
        for joint_index, joint in enumerate(joint_names):
            motor_name = config["motor_by_joint"][joint]
            actuator_index = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, motor_name)
            if actuator_index < 0 or actuator_index not in exo_indices:
                raise ValueError(f"Moteur exosquelette absent: {motor_name}")
            motor_index_by_joint[joint_index] = actuator_index

    records = []
    human_saturated = np.zeros(model.nv, dtype=int)
    exo_saturated = np.zeros(model.nv, dtype=int)
    while data.time <= times[-1] + 1e-12:
        desired_q = interpolate(data.time, times, target_qpos)
        desired_qvel = interpolate(data.time, times, target_qvel)
        desired_qacc = interpolate(data.time, times, target_qacc)
        mujoco.mj_forward(model, data)
        inertia = np.zeros(model.nv)
        mujoco.mj_mulM(model, data, inertia, desired_qacc)
        feedforward = inertia + data.qfrc_bias - data.qfrc_passive
        total = feedforward + kp * (desired_q - data.qpos) + kd * (desired_qvel - data.qvel)

        data.ctrl[:] = 0.0
        exo_torque = np.zeros(model.nv)
        for joint_index, actuator_index in motor_index_by_joint.items():
            requested = assistance[joint_index] * total[joint_index]
            lower, upper = model.actuator_ctrlrange[actuator_index]
            bounded = float(np.clip(requested, lower, upper))
            exo_saturated[joint_index] += int(bounded != requested)
            data.ctrl[actuator_index] = bounded
            exo_torque[joint_index] = bounded * model.actuator_gear[actuator_index, 0]
        requested_human = total - exo_torque
        human_torque = np.clip(requested_human, human_limits[:, 0], human_limits[:, 1])
        human_saturated += human_torque != requested_human
        data.qfrc_applied[:] = human_torque

        record = {
            "condition": condition,
            "time_s": data.time,
        }
        for index, joint in enumerate(joint_names):
            record.update({
                f"{joint}_target_rad": desired_q[index],
                f"{joint}_actual_rad": data.qpos[index],
                f"{joint}_error_rad": desired_q[index] - data.qpos[index],
                f"{joint}_human_nm": human_torque[index],
                f"{joint}_exo_nm": exo_torque[index],
            })
        records.append(record)
        mujoco.mj_step(model, data)
        if not np.all(np.isfinite(data.qpos)) or not np.all(np.isfinite(data.qvel)):
            raise RuntimeError(f"Simulation {condition} instable a t={data.time:.3f}s")

    count = len(records)
    result = {"joints": {}, "samples": count, "duration_s": float(records[-1]["time_s"])}
    for index, joint in enumerate(joint_names):
        error = np.asarray([row[f"{joint}_error_rad"] for row in records])
        human = np.asarray([row[f"{joint}_human_nm"] for row in records])
        exo = np.asarray([row[f"{joint}_exo_nm"] for row in records])
        result["joints"][joint] = {
            "tracking_rmse_deg": float(math.degrees(np.sqrt(np.mean(error * error)))),
            "tracking_peak_abs_deg": float(math.degrees(np.max(np.abs(error)))),
            "human_torque": metrics(human),
            "exo_torque": metrics(exo),
            "human_saturation_rate": float(human_saturated[index] / count),
            "exo_saturation_rate": float(exo_saturated[index] / count),
        }
    return result, records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/controllers/closed_loop_v1.json")
    args = parser.parse_args(argv)
    try:
        config = json.loads(resolve_project_path(args.config).read_text(encoding="utf-8"))
        columns, motion = read_mot(resolve_project_path(config["target_motion"]))
        results, records = {}, []
        for condition in ("unassisted", "passive", "hybrid"):
            result, condition_records = simulate(
                condition, resolve_project_path(config["models"][condition]), config, columns, motion
            )
            results[condition] = result
            records.extend(condition_records)
    except (OSError, KeyError, ValueError, RuntimeError, StopIteration, json.JSONDecodeError) as exc:
        print(f"Controle ferme impossible: {exc}", file=sys.stderr)
        return 2

    failures = []
    for condition in ("passive", "hybrid"):
        for joint, values in results[condition]["joints"].items():
            baseline_rms = results["unassisted"]["joints"][joint]["human_torque"]["rms_nm"]
            current_rms = values["human_torque"]["rms_nm"]
            values["human_torque_rms_reduction_vs_unassisted"] = 1.0 - current_rms / baseline_rms
    maximum_rmse = float(config["simulation"]["maximum_tracking_rmse_deg"])
    maximum_human_saturation = float(config["simulation"]["maximum_human_saturation_rate"])
    for condition, result in results.items():
        for joint, values in result["joints"].items():
            if values["tracking_rmse_deg"] > maximum_rmse:
                failures.append(f"{condition}/{joint}: tracking RMSE {values['tracking_rmse_deg']:.2f} deg")
            if values["human_saturation_rate"] > maximum_human_saturation:
                failures.append(f"{condition}/{joint}: saturation humaine {values['human_saturation_rate']:.1%}")
    report = {
        "schema_version": 1,
        "status": "EXPLORATORY_PASS" if not failures else "FAIL",
        "controller_id": config["controller_id"],
        "results": results,
        "thresholds": {
            "maximum_tracking_rmse_deg": maximum_rmse,
            "maximum_human_saturation_rate": maximum_human_saturation,
        },
        "failures": failures,
        "safety_overrides": {
            "all_contacts_disabled": config["simulation"]["disable_all_contacts"],
            "muscle_actuators_disabled": config["simulation"]["disable_muscle_actuators"],
        },
        "limitations": [
            "human effort is represented by ideal generalized joint torque",
            "contacts are disabled because converted meshes self-collide",
            "target motion and exoskeleton parameters remain exploratory",
        ],
    }
    dump_json(resolve_project_path(config["output_report"]), report)
    fields = list(records[0])
    write_csv_rows(resolve_project_path(config["output_timeseries"]), fields, records)
    print(f"Controle ferme: {report['status']}")
    for condition, result in results.items():
        text = ", ".join(
            f"{joint}: RMSE={values['tracking_rmse_deg']:.2f} deg, humain={values['human_torque']['rms_nm']:.2f} Nm"
            for joint, values in result["joints"].items()
        )
        print(f"- {condition}: {text}")
    for failure in failures:
        print(f"- {failure}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
