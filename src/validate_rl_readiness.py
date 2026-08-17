"""Check that validated biomechanics and an independent exoskeleton model exist before RL."""

from __future__ import annotations

import argparse
import json
import sys

from pipeline_utils import dump_json, resolve_project_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--motion-quality", default="data/results/motion_quality.json")
    parser.add_argument("--opensim-quality", default="data/results/opensim/quality.json")
    parser.add_argument("--exo-prefix", default="exo_")
    parser.add_argument("--output", default="data/results/rl_readiness.json")
    args = parser.parse_args(argv)
    failures = []
    for label, value in (("motion", args.motion_quality), ("opensim", args.opensim_quality)):
        path = resolve_project_path(value)
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
            if report.get("status") != "PASS":
                failures.append(f"qualite {label}: {report.get('status', 'UNKNOWN')}")
        except OSError:
            failures.append(f"rapport qualite {label} absent: {path}")
    try:
        import mujoco
        model = mujoco.MjModel.from_xml_path(str(resolve_project_path(args.model)))
        actuator_names = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, i) or "" for i in range(model.nu)]
        exo_actuators = [name for name in actuator_names if name.startswith(args.exo_prefix)]
        if not exo_actuators:
            failures.append(f"aucun actionneur independant {args.exo_prefix}*")
        unlimited_actuators = [
            actuator_names[i] for i in range(model.nu)
            if actuator_names[i].startswith(args.exo_prefix) and not model.actuator_ctrllimited[i]
        ]
        if unlimited_actuators:
            failures.append(f"actionneurs exo sans limites: {', '.join(unlimited_actuators)}")
        unlimited = [
            mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i) or str(i)
            for i in range(model.njnt) if not model.jnt_limited[i]
        ]
        if unlimited:
            failures.append(f"limites articulaires desactivees: {', '.join(unlimited)}")
    except (ImportError, ValueError) as exc:
        exo_actuators, unlimited, unlimited_actuators = [], [], []
        failures.append(f"modele MuJoCo invalide: {exc}")
    report = {
        "schema_version": 1, "status": "PASS" if not failures else "FAIL",
        "model": str(resolve_project_path(args.model)),
        "exo_actuators": exo_actuators, "unlimited_joints": unlimited,
        "unlimited_exo_actuators": unlimited_actuators,
        "failures": failures,
    }
    output = resolve_project_path(args.output)
    dump_json(output, report)
    print(f"Preparation RL: {report['status']}")
    for failure in failures:
        print(f"- {failure}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
