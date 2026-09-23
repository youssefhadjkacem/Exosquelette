"""Extract the right-arm rotation F-curve values to JSON for external filtering.

Part of the presentation-only smoothing pipeline (see
docs/blender/demo_smoothed_disclaimer.md). Reads the two animated channels
created by import_animation.py -- pose.bones["upperarm01.R"].rotation_euler[2]
and pose.bones["lowerarm01.R"].rotation_euler[0] -- and writes their per-frame
values (radians) to a JSON file, to be filtered by
smooth_arm_fcurve_values.py (uses scipy, not available in Blender's python)
and reinserted by apply_smoothed_arm_fcurves.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy

RIG_NAME = "Human.rig"
CHANNELS = (
    {"bone": "upperarm01.R", "data_path": "rotation_euler", "index": 2, "label": "shoulder"},
    {"bone": "lowerarm01.R", "data_path": "rotation_euler", "index": 0, "label": "elbow"},
)


def arguments():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = {"output": "arm_fcurve_values.json"}
    i = 0
    while i < len(values):
        if values[i] == "--output":
            out["output"] = values[i + 1]
            i += 2
        else:
            raise ValueError(f"Argument inconnu: {values[i]}")
    return out


def find_fcurve(action, bone_name, data_path, index):
    # Blender 5.x layered-action model: fcurves live under
    # action.layers[*].strips[*].channelbags[*].fcurves, not action.fcurves.
    target = f'pose.bones["{bone_name}"].{data_path}'
    for layer in action.layers:
        for strip in layer.strips:
            if strip.type != "KEYFRAME":
                continue
            for channelbag in strip.channelbags:
                for fcurve in channelbag.fcurves:
                    if fcurve.data_path == target and fcurve.array_index == index:
                        return fcurve
    raise ValueError(f"F-curve introuvable: {target}[{index}]")


def main():
    args = arguments()
    scene = bpy.context.scene
    rig = bpy.data.objects[RIG_NAME]
    action = rig.animation_data.action
    if action is None:
        raise ValueError("Human.rig n'a pas d'action assignee")

    frame_start, frame_end = scene.frame_start, scene.frame_end
    frames = list(range(frame_start, frame_end + 1))

    out = {"fps": scene.render.fps, "frame_start": frame_start, "frame_end": frame_end, "channels": {}}
    for channel in CHANNELS:
        fcurve = find_fcurve(action, channel["bone"], channel["data_path"], channel["index"])
        values = [fcurve.evaluate(f) for f in frames]
        out["channels"][channel["label"]] = {
            "bone": channel["bone"],
            "data_path": channel["data_path"],
            "index": channel["index"],
            "values_rad": values,
            "min_deg": min(v * 57.29577951308232 for v in values),
            "max_deg": max(v * 57.29577951308232 for v in values),
        }

    output_path = Path(args["output"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(out), encoding="utf-8")
    print(f"Extrait {len(frames)} frames -> {output_path}")
    for label, data in out["channels"].items():
        print(f"  {label}: {data['min_deg']:.3f} deg .. {data['max_deg']:.3f} deg")


if __name__ == "__main__":
    main()
