"""Rigidly recenter the ironing board under the complete wrist trajectory."""

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
    return parser.parse_args(values)


def world_bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector(tuple(min(point[axis] for point in points) for axis in range(3))),
        Vector(tuple(max(point[axis] for point in points) for axis in range(3))),
    )


def as_list(vector: Vector) -> list[float]:
    return [round(float(value), 9) for value in vector]


def main() -> None:
    args = arguments()
    scene = bpy.context.scene
    rig = bpy.data.objects[RIG_NAME]
    wrist = rig.pose.bones[WRIST_BONE]
    board = bpy.data.objects[BOARD_NAME]
    board_root = board.parent or board
    if board_root.animation_data or board_root.constraints:
        raise ValueError(f"Le parent de la planche '{board_root.name}' n'est pas statique")

    positions = []
    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        positions.append(rig.matrix_world @ wrist.head)

    wrist_minimum = Vector(tuple(min(point[axis] for point in positions) for axis in range(3)))
    wrist_maximum = Vector(tuple(max(point[axis] for point in positions) for axis in range(3)))
    wrist_center = (wrist_minimum + wrist_maximum) * 0.5
    board_minimum_before, board_maximum_before = world_bounds(board)
    board_center_before = (board_minimum_before + board_maximum_before) * 0.5
    translation = Vector((
        wrist_center.x - board_center_before.x,
        wrist_center.y - board_center_before.y,
        0.0,
    ))

    board_root.location += translation
    bpy.context.view_layer.update()
    board_minimum_after, board_maximum_after = world_bounds(board)
    board_center_after = (board_minimum_after + board_maximum_after) * 0.5

    margin_x = min(wrist_minimum.x - board_minimum_after.x, board_maximum_after.x - wrist_maximum.x)
    margin_y = min(wrist_minimum.y - board_minimum_after.y, board_maximum_after.y - wrist_maximum.y)
    report = {
        "status": "PASS" if min(margin_x, margin_y) >= 0.0 else "FAIL",
        "method": "rigid XY translation of board root; no rig, bone, keyframe, or source-data edit",
        "board": BOARD_NAME,
        "board_root": board_root.name,
        "wrist_trajectory_minimum_xyz_m": as_list(wrist_minimum),
        "wrist_trajectory_maximum_xyz_m": as_list(wrist_maximum),
        "wrist_trajectory_bbox_center_xyz_m": as_list(wrist_center),
        "board_center_before_xyz_m": as_list(board_center_before),
        "translation_xyz_m": as_list(translation),
        "board_center_after_xyz_m": as_list(board_center_after),
        "balanced_margin_x_m": round(margin_x, 9),
        "balanced_margin_y_m": round(margin_y, 9),
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
