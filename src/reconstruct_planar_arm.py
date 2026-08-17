"""Reconstruct a planar arm with fixed anthropometric segment lengths."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np


SRC_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC_ROOT))
from pipeline_utils import dump_json, parse_float, read_csv_rows, resolve_project_path, write_csv_rows  # noqa: E402
from smooth_motion import filter_valid_segments, interpolate_short_gaps  # noqa: E402
from validate_motion import analyze  # noqa: E402


MARKERS = ("r_shoulder", "r_elbow", "r_wrist")
OUTPUT_FIELDS = [
    "frame", "time_s", "source_valid", "analysis_valid", "reconstruction_method",
    "r_shoulder_x", "r_shoulder_y", "r_shoulder_z",
    "r_elbow_x", "r_elbow_y", "r_elbow_z",
    "r_wrist_x", "r_wrist_y", "r_wrist_z",
    "shoulder_planar_angle_deg", "elbow_interior_angle_deg",
]


def point(row: dict[str, str], marker: str) -> tuple[float, float]:
    return parse_float(row.get(f"{marker}_x")), parse_float(row.get(f"{marker}_y"))


def unit_direction(first: tuple[float, float], second: tuple[float, float]) -> tuple[float, float] | None:
    dx, dy_image = second[0] - first[0], second[1] - first[1]
    norm = math.hypot(dx, dy_image)
    if not math.isfinite(norm) or norm < 1e-9:
        return None
    return dx / norm, -dy_image / norm


def reconstruct_row(row: dict[str, str], upper_arm_m: float, forearm_m: float) -> dict[str, object]:
    shoulder, elbow, wrist = (point(row, marker) for marker in MARKERS)
    upper_direction = unit_direction(shoulder, elbow)
    forearm_direction = unit_direction(elbow, wrist)
    output: dict[str, object] = {
        "frame": int(parse_float(row.get("frame"))),
        "time_s": parse_float(row.get("time_s")),
        "source_valid": 0,
        "analysis_valid": 0,
        "reconstruction_method": "camera_plane_fixed_segment_lengths",
    }
    if upper_direction is None or forearm_direction is None:
        output.update({field: "" for field in OUTPUT_FIELDS if field not in output})
        return output

    shoulder_m = (0.0, 0.0, 0.0)
    elbow_m = (upper_arm_m * upper_direction[0], upper_arm_m * upper_direction[1], 0.0)
    wrist_m = (
        elbow_m[0] + forearm_m * forearm_direction[0],
        elbow_m[1] + forearm_m * forearm_direction[1],
        0.0,
    )
    dot = max(-1.0, min(1.0, upper_direction[0] * forearm_direction[0] + upper_direction[1] * forearm_direction[1]))
    output.update({
        "source_valid": 1,
        "r_shoulder_x": shoulder_m[0], "r_shoulder_y": shoulder_m[1], "r_shoulder_z": shoulder_m[2],
        "r_elbow_x": elbow_m[0], "r_elbow_y": elbow_m[1], "r_elbow_z": elbow_m[2],
        "r_wrist_x": wrist_m[0], "r_wrist_y": wrist_m[1], "r_wrist_z": wrist_m[2],
        "shoulder_planar_angle_deg": math.degrees(math.atan2(upper_direction[1], upper_direction[0])),
        "elbow_interior_angle_deg": math.degrees(math.acos(dot)),
    })
    return output


def filtered_angles(
    source_rows: list[dict[str, str]], fps: float, cutoff_hz: float, order: int,
    max_gap: int, minimum_upper_projection: float, minimum_forearm_projection: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    upper_angles, forearm_angles, reliable = [], [], []
    for row in source_rows:
        shoulder, elbow, wrist = (point(row, marker) for marker in MARKERS)
        upper_dx, upper_dy = elbow[0] - shoulder[0], -(elbow[1] - shoulder[1])
        fore_dx, fore_dy = wrist[0] - elbow[0], -(wrist[1] - elbow[1])
        upper_norm, fore_norm = math.hypot(upper_dx, upper_dy), math.hypot(fore_dx, fore_dy)
        valid = (
            math.isfinite(upper_norm) and math.isfinite(fore_norm)
            and upper_norm >= minimum_upper_projection and fore_norm >= minimum_forearm_projection
        )
        reliable.append(valid)
        upper_angles.append(math.atan2(upper_dy, upper_dx) if valid else math.nan)
        forearm_angles.append(math.atan2(fore_dy, fore_dx) if valid else math.nan)

    filtered = []
    for source in (upper_angles, forearm_angles):
        values = np.asarray(source, dtype=float)
        finite_indices = np.flatnonzero(np.isfinite(values))
        if len(finite_indices):
            filled = np.interp(np.arange(len(values)), finite_indices, values[finite_indices])
            filled = np.unwrap(filled)
            filled[~np.isfinite(values)] = np.nan
            filled, _ = interpolate_short_gaps(filled, max_gap)
            filled = filter_valid_segments(filled, fps, cutoff_hz, order)
        else:
            filled = values
        filtered.append(filled)
    return filtered[0], filtered[1], np.asarray(reliable, dtype=bool)


def reconstruct_filtered_rows(
    source_rows: list[dict[str, str]], upper_arm_m: float, forearm_m: float,
    fps: float, reconstruction: dict,
) -> tuple[list[dict[str, object]], np.ndarray, np.ndarray, np.ndarray]:
    upper_angles, _, reliable = filtered_angles(
        source_rows, fps, float(reconstruction["angle_filter_cutoff_hz"]),
        int(reconstruction["angle_filter_order"]), int(reconstruction["max_unreliable_gap_frames"]),
        float(reconstruction["min_projected_upper_arm_normalized"]),
        float(reconstruction["min_projected_forearm_normalized"]),
    )
    elbow_magnitudes, plane_signs = [], []
    for row in source_rows:
        points_3d = [
            np.asarray([parse_float(row.get(f"{marker}_{axis}")) for axis in ("x", "y", "z")], dtype=float)
            for marker in MARKERS
        ]
        shoulder_3d, elbow_3d, wrist_3d = points_3d
        upper_3d, forearm_3d = elbow_3d - shoulder_3d, wrist_3d - elbow_3d
        denominator = float(np.linalg.norm(upper_3d) * np.linalg.norm(forearm_3d))
        if np.isfinite(denominator) and denominator > 1e-12:
            cosine = float(np.clip(np.dot(upper_3d, forearm_3d) / denominator, -1.0, 1.0))
            elbow_magnitudes.append(math.acos(cosine))
        else:
            elbow_magnitudes.append(math.nan)
        shoulder_2d, elbow_2d, wrist_2d = (point(row, marker) for marker in MARKERS)
        upper_dx, upper_dy = elbow_2d[0] - shoulder_2d[0], elbow_2d[1] - shoulder_2d[1]
        fore_dx, fore_dy = wrist_2d[0] - elbow_2d[0], wrist_2d[1] - elbow_2d[1]
        cross = upper_dx * fore_dy - upper_dy * fore_dx
        if math.isfinite(cross) and abs(cross) > 1e-12:
            plane_signs.append(math.copysign(1.0, cross))
    dominant_sign = 1.0 if sum(plane_signs) >= 0 else -1.0
    elbow_magnitudes = np.asarray(elbow_magnitudes, dtype=float)
    elbow_magnitudes, _ = interpolate_short_gaps(
        elbow_magnitudes, int(reconstruction["max_unreliable_gap_frames"])
    )
    elbow_magnitudes = filter_valid_segments(
        elbow_magnitudes, fps, float(reconstruction["angle_filter_cutoff_hz"]),
        int(reconstruction["angle_filter_order"]),
    )
    forearm_angles = upper_angles + dominant_sign * elbow_magnitudes
    rows = []
    for source, upper_angle, forearm_angle in zip(source_rows, upper_angles, forearm_angles):
        output: dict[str, object] = {
            "frame": int(parse_float(source.get("frame"))),
            "time_s": parse_float(source.get("time_s")),
            "source_valid": int(math.isfinite(upper_angle) and math.isfinite(forearm_angle)),
            "analysis_valid": 0,
            "reconstruction_method": "camera_plane_fixed_segment_lengths_filtered_angles",
        }
        if not output["source_valid"]:
            output.update({field: "" for field in OUTPUT_FIELDS if field not in output})
            rows.append(output)
            continue
        upper_direction = (math.cos(upper_angle), math.sin(upper_angle))
        forearm_direction = (math.cos(forearm_angle), math.sin(forearm_angle))
        elbow_m = (upper_arm_m * upper_direction[0], upper_arm_m * upper_direction[1], 0.0)
        wrist_m = (
            elbow_m[0] + forearm_m * forearm_direction[0],
            elbow_m[1] + forearm_m * forearm_direction[1],
            0.0,
        )
        relative = math.atan2(
            math.sin(forearm_angle - upper_angle), math.cos(forearm_angle - upper_angle)
        )
        output.update({
            "r_shoulder_x": 0.0, "r_shoulder_y": 0.0, "r_shoulder_z": 0.0,
            "r_elbow_x": elbow_m[0], "r_elbow_y": elbow_m[1], "r_elbow_z": elbow_m[2],
            "r_wrist_x": wrist_m[0], "r_wrist_y": wrist_m[1], "r_wrist_z": wrist_m[2],
            "shoulder_planar_angle_deg": math.degrees(upper_angle),
            "elbow_interior_angle_deg": math.degrees(elbow_magnitudes[len(rows)]),
        })
        rows.append(output)
    return rows, upper_angles, elbow_magnitudes, reliable


def kinematic_statistics(times: np.ndarray, angles_rad: dict[str, np.ndarray]) -> dict:
    dt = float(np.median(np.diff(times)))
    output = {}
    for name, values in angles_rad.items():
        degrees = np.degrees(values)
        velocity = np.gradient(degrees, dt)
        acceleration = np.gradient(velocity, dt)
        finite = np.isfinite(degrees) & np.isfinite(velocity) & np.isfinite(acceleration)
        output[name] = {
            "samples": int(np.sum(finite)),
            "range_deg": float(np.ptp(degrees[finite])),
            "p95_abs_velocity_deg_s": float(np.percentile(np.abs(velocity[finite]), 95)),
            "max_abs_velocity_deg_s": float(np.max(np.abs(velocity[finite]))),
            "p95_abs_acceleration_deg_s2": float(np.percentile(np.abs(acceleration[finite]), 95)),
            "max_abs_acceleration_deg_s2": float(np.max(np.abs(acceleration[finite]))),
        }
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/scenarios/video1_v2.json")
    args = parser.parse_args(argv)
    try:
        config_path = resolve_project_path(args.config)
        config = json.loads(config_path.read_text(encoding="utf-8"))
        source_path = resolve_project_path(config["source_motion"])
        output_path = resolve_project_path(config["output_motion"])
        report_path = resolve_project_path(config["output_report"])
        _, source_rows = read_csv_rows(source_path)
        start = int(config["activity_window"]["start_frame"])
        end = int(config["activity_window"]["end_frame"])
        upper_arm_m = float(config["anthropometry"]["upper_arm_length_m"])
        forearm_m = float(config["anthropometry"]["forearm_length_m"])
        if upper_arm_m <= 0 or forearm_m <= 0 or end < start:
            raise ValueError("Longueurs ou fenetre d'activite invalides.")
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"Configuration V2 invalide: {exc}", file=sys.stderr)
        return 2

    selected = [row for row in source_rows if start <= int(parse_float(row.get("frame"))) <= end]
    if not selected:
        print("Aucune frame dans la fenetre d'activite.", file=sys.stderr)
        return 2
    times = np.asarray([parse_float(row.get("time_s")) for row in selected], dtype=float)
    deltas = np.diff(times)
    if len(deltas) == 0 or not np.all(np.isfinite(deltas)) or np.any(deltas <= 0):
        print("Chronologie V2 invalide.", file=sys.stderr)
        return 2
    fps = 1.0 / float(np.median(deltas))
    reconstructed, upper_angles, elbow_flexion, reliable = reconstruct_filtered_rows(
        selected, upper_arm_m, forearm_m, fps, config["reconstruction"]
    )
    write_csv_rows(output_path, OUTPUT_FIELDS, reconstructed)

    gates = config["quality_gates"]
    geometry = analyze(
        output_path,
        float(gates["max_missing_rate"]),
        float(gates["max_segment_cv"]),
        int(gates["max_frame_gap"]),
        required_markers=list(MARKERS),
    )
    kinematics = kinematic_statistics(times, {
        "shoulder_planar": upper_angles,
        "elbow_flexion": elbow_flexion,
    })
    kinematic_gates = config["kinematic_gates"]
    kinematic_failures = []
    for name, statistics in kinematics.items():
        if statistics["p95_abs_velocity_deg_s"] > float(kinematic_gates["max_p95_angular_velocity_deg_s"]):
            kinematic_failures.append(f"{name}: vitesse angulaire P95 trop elevee")
        if statistics["p95_abs_acceleration_deg_s2"] > float(kinematic_gates["max_p95_angular_acceleration_deg_s2"]):
            kinematic_failures.append(f"{name}: acceleration angulaire P95 trop elevee")
    geometric_pass = geometry["status"] == "PASS"
    exploratory_pass = geometric_pass and not kinematic_failures
    report = {
        "schema_version": 2,
        "scenario_id": config["scenario_id"],
        "status": "EXPLORATORY_PASS" if exploratory_pass else "FAIL",
        "source": str(source_path),
        "output": str(output_path),
        "task_arm": config["task_arm"],
        "activity_window": config["activity_window"],
        "anthropometry": config["anthropometry"],
        "reconstruction": config["reconstruction"],
        "valid_rows": sum(int(row["source_valid"]) for row in reconstructed),
        "total_rows": len(reconstructed),
        "raw_reliable_direction_rows": int(np.sum(reliable)),
        "geometric_quality": geometry,
        "kinematic_quality": {
            "status": "PASS" if not kinematic_failures else "FAIL",
            "statistics": kinematics,
            "thresholds": kinematic_gates,
            "failures": kinematic_failures,
        },
        "quantitative_opensim_allowed": False,
        "limitations": [
            "single camera: depth is not measured",
            "segment lengths are assumed rather than measured on the subject",
            "motion is constrained to the camera plane",
        ],
    }
    dump_json(report_path, report)
    print(f"Reconstruction V2: {report['status']}")
    print(f"Frames: {len(reconstructed)}, valides: {report['valid_rows']}")
    print(f"Mouvement: {output_path}")
    print(f"Rapport: {report_path}")
    return 0 if exploratory_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
