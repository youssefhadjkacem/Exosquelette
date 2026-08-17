"""Optimize passive joint springs on the exploratory prescribed trajectory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import mujoco
import numpy as np


SRC_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline_utils import dump_json, resolve_project_path  # noqa: E402
from evaluate_classical_assistance import inverse_torques, metrics, read_mot  # noqa: E402


def grid(specification: list[float]) -> np.ndarray:
    start, stop, step = map(float, specification)
    return np.arange(start, stop + step * 0.5, step)


def mass_only_demand(model_path: Path, columns: list[str], motion: np.ndarray, base_damping: float):
    model = mujoco.MjModel.from_xml_path(str(model_path))
    model.jnt_stiffness[:] = 0.0
    model.dof_damping[:] = base_damping
    data = mujoco.MjData(model)
    times = motion[:, 0]
    qpos = np.radians(motion[:, 1:])
    qvel = np.gradient(qpos, times, axis=0)
    qacc = np.gradient(qvel, times, axis=0)
    demand = np.zeros_like(qpos)
    for index in range(len(motion)):
        data.qpos[:] = qpos[index]
        data.qvel[:] = qvel[index]
        data.qacc[:] = qacc[index]
        mujoco.mj_inverse(model, data)
        inertia = np.zeros(model.nv)
        mujoco.mj_mulM(model, data, inertia, data.qacc)
        demand[index] = inertia + data.qfrc_bias - data.qfrc_passive
    return model, qpos, qvel, demand


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/controllers/passive_optimization_v1.json")
    args = parser.parse_args(argv)
    try:
        config = json.loads(resolve_project_path(args.config).read_text(encoding="utf-8"))
        columns, motion = read_mot(resolve_project_path(config["target_motion"]))
        baseline_model, baseline, _, _ = inverse_torques(
            resolve_project_path(config["unassisted_model"]), columns, motion
        )
        model, qpos, qvel, demand = mass_only_demand(
            resolve_project_path(config["mass_only_model"]), columns, motion,
            float(config["base_joint_damping_nms_per_rad"]),
        )
    except (OSError, KeyError, ValueError, StopIteration, json.JSONDecodeError) as exc:
        print(f"Optimisation impossible: {exc}", file=sys.stderr)
        return 2

    joint_names = [
        mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, index) for index in range(model.njnt)
    ]
    results = {}
    for joint_index, joint in enumerate(joint_names):
        search = config["search"][joint]
        best = None
        evaluated, rejected = 0, 0
        for stiffness in grid(search["stiffness_nm_per_rad"]):
            for reference in grid(search["spring_reference_rad"]):
                spring_torque = -stiffness * (qpos[:, joint_index] - reference)
                for damping in grid(search["added_damping_nms_per_rad"]):
                    passive_torque = spring_torque - damping * qvel[:, joint_index]
                    if np.max(np.abs(passive_torque)) > float(search["maximum_passive_torque_nm"]):
                        rejected += 1
                        continue
                    evaluated += 1
                    human_torque = demand[:, joint_index] - passive_torque
                    rms = float(np.sqrt(np.mean(human_torque * human_torque)))
                    candidate = (rms, float(stiffness), float(reference), float(damping), passive_torque, human_torque)
                    if best is None or candidate[0] < best[0]:
                        best = candidate
        if best is None:
            print(f"Aucun candidat admissible pour {joint}", file=sys.stderr)
            return 1
        rms, stiffness, reference, damping, passive_torque, human_torque = best
        baseline_rms = metrics(baseline[:, joint_index])["rms_nm"]
        mass_only_rms = metrics(demand[:, joint_index])["rms_nm"]
        results[joint] = {
            "stiffness_nm_per_rad": stiffness,
            "spring_reference_rad": reference,
            "added_damping_nms_per_rad": damping,
            "maximum_abs_passive_torque_nm": float(np.max(np.abs(passive_torque))),
            "human_torque_rms_nm": rms,
            "unassisted_rms_nm": baseline_rms,
            "mass_only_rms_nm": mass_only_rms,
            "rms_reduction_vs_unassisted": 1.0 - rms / baseline_rms,
            "evaluated_candidates": evaluated,
            "rejected_candidates": rejected,
        }
    report = {
        "schema_version": 1,
        "status": "EXPLORATORY_PASS",
        "optimization_id": config["optimization_id"],
        "objective": "minimize RMS residual human joint torque",
        "contact_constraints_excluded": True,
        "recommended_parameters": results,
        "limitations": [
            "optimized on one exploratory monocular trajectory",
            "parameters may overfit the ironing pilot case",
            "interface forces and comfort are not yet included",
        ],
    }
    dump_json(resolve_project_path(config["output_report"]), report)
    print("Optimisation passive: EXPLORATORY_PASS")
    for joint, result in results.items():
        print(
            f"- {joint}: k={result['stiffness_nm_per_rad']:.3f}, "
            f"ref={result['spring_reference_rad']:.3f}, RMS={result['human_torque_rms_nm']:.3f} Nm, "
            f"reduction={result['rms_reduction_vs_unassisted']:.1%}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
