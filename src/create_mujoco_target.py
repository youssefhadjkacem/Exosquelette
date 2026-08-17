"""Map constrained V2 angles to an exploratory arm26 OpenSim/MuJoCo MOT target."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path

import mujoco


SRC_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC_ROOT))
from pipeline_utils import dump_json, parse_float, read_csv_rows, resolve_project_path  # noqa: E402


def map_angles(row: dict[str, str], mapping: dict) -> dict[str, float]:
    shoulder = mapping["shoulder"]
    elbow = mapping["elbow"]
    return {
        shoulder["target_coordinate"]: float(shoulder["scale"]) * (
            parse_float(row.get(shoulder["source_column"])) - float(shoulder["reference_axis_deg"])
        ),
        elbow["target_coordinate"]: float(elbow["scale"]) * parse_float(
            row.get(elbow["source_column"])
        ) + float(elbow["offset_deg"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/scenarios/video1_v2.json")
    args = parser.parse_args(argv)
    try:
        config_path = resolve_project_path(args.config)
        config = json.loads(config_path.read_text(encoding="utf-8"))
        _, rows = read_csv_rows(resolve_project_path(config["output_motion"]))
        mapping = config["mujoco_mapping"]
        model = mujoco.MjModel.from_xml_path(str(resolve_project_path(mapping["model"])))
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"Mapping MuJoCo impossible: {exc}", file=sys.stderr)
        return 2

    joint_limits = {}
    for joint in (mapping["shoulder"]["target_coordinate"], mapping["elbow"]["target_coordinate"]):
        index = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint)
        if index < 0 or not model.jnt_limited[index]:
            print(f"Articulation absente ou non limitee: {joint}", file=sys.stderr)
            return 2
        joint_limits[joint] = [math.degrees(value) for value in model.jnt_range[index]]

    times, mapped, clipped = [], [], {joint: 0 for joint in joint_limits}
    for row in rows:
        values = map_angles(row, mapping)
        if not all(math.isfinite(value) for value in values.values()):
            print(f"Angle V2 manquant a la frame {row.get('frame')}", file=sys.stderr)
            return 1
        for joint, value in values.items():
            lower, upper = joint_limits[joint]
            bounded = min(max(value, lower), upper)
            clipped[joint] += int(bounded != value)
            values[joint] = bounded
        times.append(parse_float(row.get("time_s")))
        mapped.append(values)
    if len(times) < 2 or any(b <= a for a, b in zip(times, times[1:])):
        print("Chronologie cible invalide.", file=sys.stderr)
        return 2

    output = resolve_project_path(config["output_mot"])
    output.parent.mkdir(parents=True, exist_ok=True)
    joints = list(joint_limits)
    with output.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("arm26 exploratory target\n")
        stream.write(f"nRows={len(rows)}\n")
        stream.write(f"nColumns={len(joints) + 1}\n")
        stream.write("inDegrees=yes\n")
        stream.write("endheader\n")
        stream.write("time\t" + "\t".join(joints) + "\n")
        for time_s, values in zip(times, mapped):
            stream.write(f"{time_s:.8f}\t" + "\t".join(f"{values[joint]:.8f}" for joint in joints) + "\n")

    report = {
        "schema_version": 1,
        "status": "EXPLORATORY_PASS",
        "source": config["output_motion"],
        "output": config["output_mot"],
        "mapping_status": mapping["status"],
        "rows": len(rows),
        "fps": 1.0 / statistics.median(b - a for a, b in zip(times, times[1:])),
        "joint_limits_deg": joint_limits,
        "clipped_frames": clipped,
        "clipped_rates": {joint: count / len(rows) for joint, count in clipped.items()},
        "ranges_deg": {
            joint: [min(row[joint] for row in mapped), max(row[joint] for row in mapped)] for joint in joints
        },
        "limitations": [
            "camera vertical is assumed to match the model elevation reference",
            "elbow angle is a filtered MediaPipe proxy",
            "joint-limit clipping changes the measured proxy when necessary",
        ],
    }
    dump_json(resolve_project_path(config["output_mot_report"]), report)
    print(f"Cible MuJoCo: {output}")
    print(f"Mapping: {report['status']}; frames={len(rows)}")
    for joint in joints:
        print(f"- {joint}: plage={report['ranges_deg'][joint]}, ecretage={report['clipped_rates'][joint]:.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
