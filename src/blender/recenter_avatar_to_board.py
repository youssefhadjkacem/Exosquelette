"""Rigidly recenter the complete avatar wrist trajectory over the board."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


RIG_NAME = "Human.rig"
WRIST_BONE = "wrist.R"
BOARD_NAME = "White_desk"


def arguments() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--translation")
    return parser.parse_args(values)


def world_bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector(tuple(min(point[axis] for point in points) for axis in range(3))),
        Vector(tuple(max(point[axis] for point in points) for axis in range(3))),
    )


def vector_list(value: Vector) -> list[float]:
    return [round(float(component), 9) for component in value]


def main() -> None:
    args = arguments()
    scene = bpy.context.scene
    rig = bpy.data.objects[RIG_NAME]
    wrist = rig.pose.bones[WRIST_BONE]
    board = bpy.data.objects[BOARD_NAME]
    if rig.animation_data is None:
        raise ValueError("Le rig ne contient aucune animation")

    positions = []
    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        positions.append(rig.matrix_world @ wrist.head)

    wrist_minimum = Vector(tuple(min(point[axis] for point in positions) for axis in range(3)))
    wrist_maximum = Vector(tuple(max(point[axis] for point in positions) for axis in range(3)))
    wrist_center_before = (wrist_minimum + wrist_maximum) * 0.5
    board_minimum, board_maximum = world_bounds(board)
    board_center = (board_minimum + board_maximum) * 0.5
    if args.translation:
        values = [float(value) for value in args.translation.split(",")]
        if len(values) != 3:
            raise ValueError("--translation attend x,y,z")
        translation = Vector(values)
    else:
        translation = Vector((
            board_center.x - wrist_center_before.x,
            board_center.y - wrist_center_before.y,
            0.0,
        ))

    rig_location_before = rig.location.copy()
    rig.location += translation
    bpy.context.view_layer.update()
    wrist_minimum_after = wrist_minimum + translation
    wrist_maximum_after = wrist_maximum + translation
    wrist_center_after = (wrist_minimum_after + wrist_maximum_after) * 0.5
    margin_x = min(
        wrist_minimum_after.x - board_minimum.x,
        board_maximum.x - wrist_maximum_after.x,
    )
    margin_y = min(
        wrist_minimum_after.y - board_minimum.y,
        board_maximum.y - wrist_maximum_after.y,
    )

    report = {
        "status": "PASS" if min(margin_x, margin_y) >= 0.0 else "FAIL",
        "method": "rigid XY translation of Human.rig root; no bone or keyframe edit",
        "rig": RIG_NAME,
        "rig_children_moved": [child.name for child in rig.children],
        "translation_xyz_m": vector_list(translation),
        "rig_location_before_xyz_m": vector_list(rig_location_before),
        "rig_location_after_xyz_m": vector_list(rig.location),
        "board_center_xyz_m": vector_list(board_center),
        "wrist_center_before_xyz_m": vector_list(wrist_center_before),
        "wrist_center_after_xyz_m": vector_list(wrist_center_after),
        "balanced_margin_x_m": round(margin_x, 9),
        "balanced_margin_y_m": round(margin_y, 9),
        "z_translation_m": float(translation.z),
    }

    scene.frame_set(scene.frame_start)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
