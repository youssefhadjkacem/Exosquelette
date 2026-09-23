"""Adjust only the visual avatar's right-arm proportions using pose scales.

The animation's rotation keyframes and all source biomechanics files are left
untouched.  Constant local-Y bone scales let the Armature modifier stretch the
skin and garment with their existing vertex weights.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy


UPPER_BONES = ("upperarm01.R", "upperarm02.R")
LOWER_BONES = ("lowerarm01.R", "lowerarm02.R")
TARGET_UPPER_M = 0.30
TARGET_LOWER_M = 0.25
RIG_CLEARANCE_Z_M = 0.0337
CHECK_FRAMES = (1, 181, 541, 1081)


def arguments():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    return parser.parse_args(values)


def joint_distance(rig, first, second):
    return float(((rig.matrix_world @ rig.pose.bones[first].head) -
                  (rig.matrix_world @ rig.pose.bones[second].head)).length)


def set_scales(rig, upper, lower):
    for name in UPPER_BONES:
        rig.pose.bones[name].scale = (1.0, upper, 1.0)
    for name in LOWER_BONES:
        rig.pose.bones[name].scale = (1.0, lower, 1.0)
    bpy.context.view_layer.update()


def solve_scale(scene, rig, segment, target, fixed_upper=1.0, fixed_lower=1.0):
    low, high = 0.5, 2.5
    for _ in range(36):
        middle = (low + high) * 0.5
        if segment == "upper":
            set_scales(rig, middle, fixed_lower)
            measured = joint_distance(rig, "upperarm01.R", "lowerarm01.R")
        else:
            set_scales(rig, fixed_upper, middle)
            measured = joint_distance(rig, "lowerarm01.R", "wrist.R")
        if measured < target:
            low = middle
        else:
            high = middle
    return (low + high) * 0.5


def main():
    args = arguments()
    scene = bpy.context.scene
    rig = bpy.data.objects["Human.rig"]
    scene.frame_set(1)
    bpy.context.view_layer.update()

    before = {
        "upper_m": joint_distance(rig, "upperarm01.R", "lowerarm01.R"),
        "lower_m": joint_distance(rig, "lowerarm01.R", "wrist.R"),
    }
    # Isolate the forearm from the upper-arm non-uniform scale, and the hand
    # from the forearm scale. Bone heads still follow their parents, while
    # segment thickness and hand size are not multiplied downstream.
    rig.data.bones["lowerarm01.R"].inherit_scale = "NONE"
    rig.data.bones["wrist.R"].inherit_scale = "NONE"
    bpy.context.view_layer.update()
    upper_scale = solve_scale(scene, rig, "upper", TARGET_UPPER_M)
    lower_scale = solve_scale(scene, rig, "lower", TARGET_LOWER_M, fixed_upper=upper_scale)
    # Re-solve upper once after the lower scale in case inherited transforms
    # couple the two segments, then finalize the lower target.
    upper_scale = solve_scale(scene, rig, "upper", TARGET_UPPER_M, fixed_lower=lower_scale)
    lower_scale = solve_scale(scene, rig, "lower", TARGET_LOWER_M, fixed_upper=upper_scale)
    set_scales(rig, upper_scale, lower_scale)
    rig.location.z += RIG_CLEARANCE_Z_M
    bpy.context.view_layer.update()

    samples = []
    for frame in CHECK_FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        samples.append({
            "frame": frame,
            "shoulder_elbow_m": joint_distance(rig, "upperarm01.R", "lowerarm01.R"),
            "elbow_wrist_m": joint_distance(rig, "lowerarm01.R", "wrist.R"),
        })

    rig["visual_v2_arm_proportions"] = True
    rig["visual_upper_arm_target_m"] = TARGET_UPPER_M
    rig["visual_forearm_target_m"] = TARGET_LOWER_M
    rig["visual_arm_proportions_note"] = (
        "Visual avatar only; OpenSim arm26_scaled.osim and RL remain unchanged."
    )
    scene.frame_set(1)
    report = {
        "status": "PASS" if all(
            abs(s["shoulder_elbow_m"] - TARGET_UPPER_M) < 1e-5 and
            abs(s["elbow_wrist_m"] - TARGET_LOWER_M) < 1e-5
            for s in samples
        ) else "FAIL",
        "method": "constant pose-bone local-Y scaling; no animation keyframe edits",
        "before": before,
        "targets_m": {"upper": TARGET_UPPER_M, "lower": TARGET_LOWER_M},
        "bone_scales": {
            "upperarm01.R_y": upper_scale,
            "upperarm02.R_y": upper_scale,
            "lowerarm01.R_y": lower_scale,
            "lowerarm02.R_y": lower_scale,
        },
        "scale_inheritance": {
            "lowerarm01.R": rig.data.bones["lowerarm01.R"].inherit_scale,
            "wrist.R": rig.data.bones["wrist.R"].inherit_scale,
        },
        "rig_clearance_translation_z_m": RIG_CLEARANCE_Z_M,
        "rig_clearance_translation_z_cm": RIG_CLEARANCE_Z_M * 100.0,
        "samples": samples,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
