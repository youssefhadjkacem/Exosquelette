"""Inspect a converted MuJoCo model and report biomechanical/RL readiness issues."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_ROOT))
from pipeline_utils import dump_json, resolve_project_path  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", default="data/results/mujoco_model_quality.json")
    parser.add_argument("--exo-prefix", default="exo_")
    args = parser.parse_args(argv)
    try:
        import mujoco
        path = resolve_project_path(args.model)
        model = mujoco.MjModel.from_xml_path(str(path))
        data = mujoco.MjData(model)
        mujoco.mj_step(model, data)
    except (ImportError, ValueError) as exc:
        print(f"Modele MuJoCo invalide: {exc}", file=sys.stderr)
        return 2
    joint_names = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i) or str(i) for i in range(model.njnt)]
    actuator_names = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, i) or str(i) for i in range(model.nu)]
    unlimited = [joint_names[i] for i in range(model.njnt) if not model.jnt_limited[i]]
    exo = [name for name in actuator_names if name.startswith(args.exo_prefix)]
    warnings = []
    if unlimited:
        warnings.append(f"limites desactivees: {', '.join(unlimited)}")
    if not exo:
        warnings.append(f"aucun actionneur {args.exo_prefix}*; RL actif interdit")
    report = {
        "schema_version": 1, "status": "PASS" if not warnings else "FAIL",
        "model": str(path), "nq": model.nq, "nv": model.nv,
        "bodies": model.nbody, "joints": joint_names,
        "actuators": actuator_names, "exo_actuators": exo,
        "unlimited_joints": unlimited, "warnings": warnings,
    }
    dump_json(resolve_project_path(args.output), report)
    print(f"Modele MuJoCo: {report['status']}; nq={model.nq}, nv={model.nv}, nu={model.nu}")
    for warning in warnings:
        print(f"- {warning}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
