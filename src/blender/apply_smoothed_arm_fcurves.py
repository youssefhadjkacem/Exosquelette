"""Reinsert Butterworth-filtered arm angle values into femme_demo_smoothed.blend.

COSMETIC / PRESENTATION-ONLY STEP. This overwrites the two right-arm rotation
F-curves (upperarm01.R rotation_euler[2], lowerarm01.R rotation_euler[0]) on
whichever file is passed in with the values produced by
smooth_arm_fcurve_values.py. It must only ever be run against the
femme_demo_smoothed.blend copy, never against the validated reference
femme.blend -- see docs/blender/demo_smoothed_disclaimer.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy

RIG_NAME = "Human.rig"


def arguments():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = {"input": None, "output": None}
    i = 0
    while i < len(values):
        if values[i] == "--input":
            out["input"] = values[i + 1]
            i += 2
        elif values[i] == "--output":
            out["output"] = values[i + 1]
            i += 2
        else:
            raise ValueError(f"Argument inconnu: {values[i]}")
    if out["input"] is None or out["output"] is None:
        raise ValueError("--input et --output sont requis")
    return out


def find_fcurve(action, bone_name, data_path, index):
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
    data = json.loads(Path(args["input"]).read_text(encoding="utf-8"))
    rig = bpy.data.objects[RIG_NAME]
    action = rig.animation_data.action
    frame_start = data["frame_start"]

    for label, channel in data["channels"].items():
        fcurve = find_fcurve(action, channel["bone"], channel["data_path"], channel["index"])
        values = channel["values_rad"]
        if len(fcurve.keyframe_points) != len(values):
            raise ValueError(
                f"{label}: {len(fcurve.keyframe_points)} keyframes existants != {len(values)} valeurs filtrees"
            )
        for index, keyframe in enumerate(fcurve.keyframe_points):
            frame = frame_start + index
            if round(keyframe.co.x) != frame:
                raise ValueError(f"{label}: keyframe {index} a la frame {keyframe.co.x}, attendu {frame}")
            keyframe.co.y = values[index]
            keyframe.handle_left.y = values[index]
            keyframe.handle_right.y = values[index]
        fcurve.update()

    rig["demo_smoothed_cosmetic_only"] = True
    rig["demo_smoothed_note"] = (
        "Arm rotation F-curves Butterworth-filtered (order=4, cutoff=1.5Hz, zero-phase) "
        "for presentation fluidity only. NOT for biomechanical claims -- use femme.blend."
    )
    rig["demo_smoothed_filter"] = json.dumps(data["filter"]) if "filter" in data else "unknown"

    bpy.context.view_layer.update()
    output = Path(args["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    print(f"Sauvegarde: {output}")


if __name__ == "__main__":
    main()
