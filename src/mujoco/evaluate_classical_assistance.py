"""Compare unassisted, passive and classical hybrid assistance on prescribed motion."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import mujoco
import numpy as np


SRC_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_ROOT))
from pipeline_utils import dump_json, resolve_project_path, write_csv_rows  # noqa: E402


def read_mot(path: Path) -> tuple[list[str], np.ndarray]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    end = next(index for index, line in enumerate(lines) if line.strip().lower() == "endheader")
    columns = lines[end + 1].split()
    data = np.asarray([[float(value) for value in line.split()] for line in lines[end + 2:] if line.strip()])
    if data.ndim != 2 or data.shape[1] != len(columns):
        raise ValueError(f"MOT invalide: {path}")
    return columns, data


def inverse_torques(model_path: Path, columns: list[str], motion: np.ndarray) -> tuple[mujoco.MjModel, np.ndarray, np.ndarray, np.ndarray]:
    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)
    times = motion[:, 0]
    qpos = np.zeros((len(motion), model.nq))
    joints = []
    for joint_index in range(model.njnt):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, joint_index)
        if name not in columns:
            raise ValueError(f"Coordonnee cible absente: {name}")
        qpos_index = model.jnt_qposadr[joint_index]
        qpos[:, qpos_index] = np.radians(motion[:, columns.index(name)])
        joints.append(name)
    qvel = np.gradient(qpos, times, axis=0)
    qacc = np.gradient(qvel, times, axis=0)
    torques = np.zeros((len(motion), model.nv))
    constraint_torques = np.zeros((len(motion), model.nv))
    for index in range(len(motion)):
        data.qpos[:] = qpos[index]
        data.qvel[:] = qvel[index]
        data.qacc[:] = qacc[index]
        mujoco.mj_inverse(model, data)
        inertia_torque = np.zeros(model.nv)
        mujoco.mj_mulM(model, data, inertia_torque, data.qacc)
        torques[index] = inertia_torque + data.qfrc_bias - data.qfrc_passive
        constraint_torques[index] = data.qfrc_constraint
    return model, torques, qvel, constraint_torques


def metrics(values: np.ndarray) -> dict:
    return {
        "rms_nm": float(np.sqrt(np.mean(values * values))),
        "mean_abs_nm": float(np.mean(np.abs(values))),
        "peak_abs_nm": float(np.max(np.abs(values))),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/controllers/classical_assistance_v1.json")
    args = parser.parse_args(argv)
    try:
        config = json.loads(resolve_project_path(args.config).read_text(encoding="utf-8"))
        columns, motion = read_mot(resolve_project_path(config["target_motion"]))
        baseline_model, baseline_torque, _, baseline_constraints = inverse_torques(resolve_project_path(config["models"]["unassisted"]), columns, motion)
        passive_model, passive_torque, _, passive_constraints = inverse_torques(resolve_project_path(config["models"]["passive"]), columns, motion)
        hybrid_model, hybrid_required, qvel, hybrid_constraints = inverse_torques(resolve_project_path(config["models"]["hybrid"]), columns, motion)
    except (OSError, KeyError, ValueError, StopIteration, json.JSONDecodeError) as exc:
        print(f"Evaluation impossible: {exc}", file=sys.stderr)
        return 2

    joint_names = [
        mujoco.mj_id2name(hybrid_model, mujoco.mjtObj.mjOBJ_JOINT, index)
        for index in range(hybrid_model.njnt)
    ]
    exo_torque = np.zeros_like(hybrid_required)
    clipping = {}
    for joint_index, joint in enumerate(joint_names):
        motor_name = config["motor_by_joint"][joint]
        actuator_index = mujoco.mj_name2id(hybrid_model, mujoco.mjtObj.mjOBJ_ACTUATOR, motor_name)
        limits = hybrid_model.actuator_ctrlrange[actuator_index]
        requested = float(config["assistance_fraction"][joint]) * hybrid_required[:, joint_index]
        exo_torque[:, joint_index] = np.clip(requested, limits[0], limits[1])
        clipping[joint] = float(np.mean(exo_torque[:, joint_index] != requested))
    human_hybrid = hybrid_required - exo_torque

    conditions = {
        "unassisted": baseline_torque,
        "passive": passive_torque,
        "hybrid_classical": human_hybrid,
    }
    report_metrics = {}
    for condition, torques in conditions.items():
        report_metrics[condition] = {
            joint: metrics(torques[:, index]) for index, joint in enumerate(joint_names)
        }
    for joint_index, joint in enumerate(joint_names):
        baseline_rms = report_metrics["unassisted"][joint]["rms_nm"]
        for condition in ("passive", "hybrid_classical"):
            current = report_metrics[condition][joint]["rms_nm"]
            report_metrics[condition][joint]["rms_reduction_vs_unassisted"] = 1.0 - current / baseline_rms

    power = exo_torque * qvel
    times = motion[:, 0]
    report = {
        "schema_version": 1,
        "status": "EXPLORATORY_PASS",
        "controller_id": config["controller_id"],
        "evaluation_mode": "prescribed_kinematics_inverse_dynamics",
        "contact_constraints_excluded_from_required_torque": True,
        "rows": len(motion),
        "time_range_s": [float(times[0]), float(times[-1])],
        "metrics": report_metrics,
        "exo": {
            "clipping_rate": clipping,
            "rms_torque_nm": {joint: metrics(exo_torque[:, i])["rms_nm"] for i, joint in enumerate(joint_names)},
            "absolute_mechanical_energy_j": {
                joint: float(np.trapz(np.abs(power[:, i]), times)) for i, joint in enumerate(joint_names)
            },
        },
        "contact_diagnostic": {
            "maximum_abs_constraint_torque_nm": {
                "unassisted": float(np.max(np.abs(baseline_constraints))),
                "passive": float(np.max(np.abs(passive_constraints))),
                "hybrid": float(np.max(np.abs(hybrid_constraints))),
            },
            "interpretation": "Large values are converted-mesh contact artefacts and are excluded from this joint-torque proxy."
        },
        "limitations": [
            "trajectory is prescribed rather than dynamically tracked",
            "inverse dynamics uses exploratory monocular kinematics",
            "human residual joint torque is a proxy, not muscle activation",
            "converted mesh contacts require cleanup before physical contact simulation",
        ],
    }
    dump_json(resolve_project_path(config["output_report"]), report)

    fields = ["time_s"]
    for joint in joint_names:
        fields.extend([
            f"{joint}_unassisted_nm", f"{joint}_passive_nm",
            f"{joint}_exo_nm", f"{joint}_human_hybrid_nm",
        ])
    rows = []
    for frame_index, time_s in enumerate(times):
        row = {"time_s": time_s}
        for joint_index, joint in enumerate(joint_names):
            row.update({
                f"{joint}_unassisted_nm": baseline_torque[frame_index, joint_index],
                f"{joint}_passive_nm": passive_torque[frame_index, joint_index],
                f"{joint}_exo_nm": exo_torque[frame_index, joint_index],
                f"{joint}_human_hybrid_nm": human_hybrid[frame_index, joint_index],
            })
        rows.append(row)
    write_csv_rows(resolve_project_path(config["output_timeseries"]), fields, rows)
    print("Evaluation classique: EXPLORATORY_PASS")
    for condition in conditions:
        values = ", ".join(
            f"{joint} RMS={report_metrics[condition][joint]['rms_nm']:.3f} Nm" for joint in joint_names
        )
        print(f"- {condition}: {values}")
    print(f"Rapport: {resolve_project_path(config['output_report'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
