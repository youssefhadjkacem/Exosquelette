"""Measure the right-wrist trajectory against the ironing-board footprint."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
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
    parser.add_argument("--csv", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--mot")
    return parser.parse_args(values)


def world_bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector(tuple(min(point[axis] for point in points) for axis in range(3))),
        Vector(tuple(max(point[axis] for point in points) for axis in range(3))),
    )


def consecutive_ranges(frames: list[int]) -> list[dict[str, int]]:
    if not frames:
        return []
    ranges = []
    start = previous = frames[0]
    for frame in frames[1:]:
        if frame != previous + 1:
            ranges.append({"start": start, "end": previous, "count": previous - start + 1})
            start = frame
        previous = frame
    ranges.append({"start": start, "end": previous, "count": previous - start + 1})
    return ranges


def pearson(first: list[float], second: list[float]) -> float:
    first_mean = statistics.fmean(first)
    second_mean = statistics.fmean(second)
    numerator = sum((a - first_mean) * (b - second_mean) for a, b in zip(first, second))
    denominator = math.sqrt(
        sum((value - first_mean) ** 2 for value in first)
        * sum((value - second_mean) ** 2 for value in second)
    )
    return numerator / denominator


def read_mot(path: Path) -> list[dict[str, float]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    end = next(index for index, line in enumerate(lines) if line.strip().lower() == "endheader")
    reader = csv.DictReader(lines[end + 1 :], delimiter="\t")
    return [{key: float(value) for key, value in row.items()} for row in reader]


def main() -> None:
    args = arguments()
    scene = bpy.context.scene
    rig = bpy.data.objects[RIG_NAME]
    wrist = rig.pose.bones[WRIST_BONE]
    board = bpy.data.objects[BOARD_NAME]
    board_minimum, board_maximum = world_bounds(board)

    rows = []
    outside_frames = []
    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        # The head of wrist.R is the anatomical wrist joint. Its tail points
        # into the hand and would bias the test toward the fingers.
        position = rig.matrix_world @ wrist.head
        dx_low = max(board_minimum.x - position.x, 0.0)
        dx_high = max(position.x - board_maximum.x, 0.0)
        dy_low = max(board_minimum.y - position.y, 0.0)
        dy_high = max(position.y - board_maximum.y, 0.0)
        dx = dx_low + dx_high
        dy = dy_low + dy_high
        outside_distance = math.hypot(dx, dy)
        inside_xy = outside_distance <= 1e-9
        if not inside_xy:
            outside_frames.append(frame)
        side = []
        if dx_low:
            side.append("x_min")
        if dx_high:
            side.append("x_max")
        if dy_low:
            side.append("y_min")
        if dy_high:
            side.append("y_max")
        rows.append({
            "frame": frame,
            "time_s": (frame - scene.frame_start) / scene.render.fps,
            "wrist_x_m": position.x,
            "wrist_y_m": position.y,
            "wrist_z_m": position.z,
            "inside_board_xy": inside_xy,
            "outside_side": "+".join(side),
            "outside_dx_m": dx,
            "outside_dy_m": dy,
            "outside_distance_m": outside_distance,
            "height_above_board_top_m": position.z - board_maximum.z,
        })

    csv_path = Path(args.csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    maximum_row = max(rows, key=lambda row: row["outside_distance_m"])
    focus_rows = [row for row in rows if 181 <= row["frame"] <= 192]
    scene.frame_set(scene.frame_start)
    bpy.context.view_layer.update()
    shoulder_position = rig.matrix_world @ rig.pose.bones["upperarm01.R"].head
    elbow_position = rig.matrix_world @ rig.pose.bones["lowerarm01.R"].head
    wrist_position = rig.matrix_world @ wrist.head
    report = {
        "blend_file": bpy.data.filepath,
        "coordinate_system": "Blender world coordinates, metres",
        "wrist": {
            "rig": RIG_NAME,
            "bone": WRIST_BONE,
            "sample_point": "bone head (anatomical wrist joint)",
        },
        "board": {
            "object": BOARD_NAME,
            "minimum_xyz_m": list(board_minimum),
            "maximum_xyz_m": list(board_maximum),
            "width_x_m": board_maximum.x - board_minimum.x,
            "depth_y_m": board_maximum.y - board_minimum.y,
            "top_z_m": board_maximum.z,
        },
        "frames": {
            "start": scene.frame_start,
            "end": scene.frame_end,
            "count": len(rows),
            "fps": scene.render.fps,
        },
        "outside": {
            "count": len(outside_frames),
            "percentage": 100.0 * len(outside_frames) / len(rows),
            "ranges": consecutive_ranges(outside_frames),
            "maximum_distance_m": maximum_row["outside_distance_m"],
            "maximum_distance_frame": maximum_row["frame"],
            "maximum_distance_side": maximum_row["outside_side"],
            "maximum_distance_position_xyz_m": [
                maximum_row["wrist_x_m"], maximum_row["wrist_y_m"], maximum_row["wrist_z_m"]
            ],
        },
        "focus_181_192": focus_rows,
        "trajectory_extents_xyz_m": {
            "minimum": [min(row[key] for row in rows) for key in ("wrist_x_m", "wrist_y_m", "wrist_z_m")],
            "maximum": [max(row[key] for row in rows) for key in ("wrist_x_m", "wrist_y_m", "wrist_z_m")],
        },
        "scene_alignment": {
            "frame_1_wrist_margin_to_near_y_edge_m": board_maximum.y - rows[0]["wrist_y_m"],
            "frame_1_shoulder_to_near_y_edge_m": shoulder_position.y - board_maximum.y,
            "rig_scale_xyz": list(rig.scale),
            "upper_arm_length_m": (elbow_position - shoulder_position).length,
            "forearm_length_m": (wrist_position - elbow_position).length,
        },
    }
    if args.mot:
        mot_rows = read_mot(Path(args.mot))
        if len(mot_rows) != len(rows):
            raise ValueError(f"MOT rows={len(mot_rows)} but trajectory rows={len(rows)}")
        shoulder_angles = [row["r_shoulder_elev"] for row in mot_rows]
        elbow_angles = [row["r_elbow_flex"] for row in mot_rows]
        wrist_y = [row["wrist_y_m"] for row in rows]
        outside_mask = [not row["inside_board_xy"] for row in rows]
        outside_elbow_angles = [
            angle for angle, outside in zip(elbow_angles, outside_mask) if outside
        ]
        inside_elbow_angles = [
            angle for angle, outside in zip(elbow_angles, outside_mask) if not outside
        ]
        report["source_angle_diagnostics"] = {
            "mot": str(Path(args.mot)),
            "shoulder_range_deg": [min(shoulder_angles), max(shoulder_angles)],
            "shoulder_amplitude_deg": max(shoulder_angles) - min(shoulder_angles),
            "elbow_range_deg": [min(elbow_angles), max(elbow_angles)],
            "elbow_amplitude_deg": max(elbow_angles) - min(elbow_angles),
            "correlation_wrist_y_shoulder": pearson(wrist_y, shoulder_angles),
            "correlation_wrist_y_elbow": pearson(wrist_y, elbow_angles),
            "mean_elbow_outside_deg": (
                statistics.fmean(outside_elbow_angles) if outside_elbow_angles else None
            ),
            "mean_elbow_inside_deg": (
                statistics.fmean(inside_elbow_angles) if inside_elbow_angles else None
            ),
        }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
