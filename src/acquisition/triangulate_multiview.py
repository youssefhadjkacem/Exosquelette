"""Triangulate two synchronized 2D pose streams into 3D (multiview steps D+E).

Consumes the per-camera pixel-landmark CSVs from detect_pose_2d.py (step B)
and a stereo calibration file (derive_intrinsic_calibration.py, or a real
checkerboard calibration with the same schema), and produces:

  - a canonical motion CSV matching docs/data_contract.md exactly, so it
    plugs directly into smooth_motion.py -> validate_motion.py ->
    convert_to_trc.py without changing any of those three scripts;
  - a triangulation quality report (reprojection error, marker coverage).

Assumes the two input CSVs are already frame-aligned (same row i = same
instant in both views, within the residual sync error already measured for
the session) -- it does not re-synchronize anything.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]

LANDMARKS = (
    "r_shoulder", "r_elbow", "r_wrist",
    "l_shoulder", "l_elbow", "l_wrist",
    "r_hip", "l_hip",
)


def resolve_project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"CSV sans en-tete: {path}")
        return list(reader.fieldnames), list(reader)


def write_csv_rows(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def dump_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def parse_float(value: object) -> float:
    if value is None or value == "":
        return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def projection_matrix(camera: dict) -> np.ndarray:
    k = np.array(camera["intrinsic_matrix"], dtype=float)
    r = np.array(camera["extrinsic"]["rotation_world_to_camera"], dtype=float)
    t = np.array(camera["extrinsic"]["translation_world_to_camera_m"], dtype=float).reshape(3, 1)
    rt = np.hstack([r, t])
    return k @ rt


def triangulate_point(p1: np.ndarray, p2: np.ndarray, pt1_px: tuple[float, float], pt2_px: tuple[float, float]) -> np.ndarray:
    pts1 = np.array([[pt1_px[0]], [pt1_px[1]]], dtype=float)
    pts2 = np.array([[pt2_px[0]], [pt2_px[1]]], dtype=float)
    import cv2
    homogeneous = cv2.triangulatePoints(p1, p2, pts1, pts2)
    return (homogeneous[:3] / homogeneous[3]).flatten()


def reproject(p: np.ndarray, point_3d: np.ndarray) -> tuple[float, float]:
    homogeneous_3d = np.append(point_3d, 1.0)
    projected = p @ homogeneous_3d
    return projected[0] / projected[2], projected[1] / projected[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pose-camera-1", required=True)
    parser.add_argument("--pose-camera-2", required=True)
    parser.add_argument("--calibration", required=True)
    parser.add_argument("--output", required=True, help="Canonical motion CSV (data_contract.md schema)")
    parser.add_argument("--quality-output", required=True)
    parser.add_argument("--min-visibility", type=float, default=0.5)
    parser.add_argument("--max-reprojection-error-px", type=float, default=3.0)
    args = parser.parse_args(argv)

    calibration = json.loads(resolve_project_path(args.calibration).read_text(encoding="utf-8"))
    cameras_by_role = {cam["name"]: cam for cam in calibration["cameras"]}
    if "camera_1" not in cameras_by_role or "camera_2" not in cameras_by_role:
        raise SystemExit("Le fichier de calibration doit contenir camera_1 et camera_2.")
    p1 = projection_matrix(cameras_by_role["camera_1"])
    p2 = projection_matrix(cameras_by_role["camera_2"])

    _, rows1 = read_csv_rows(resolve_project_path(args.pose_camera_1))
    _, rows2 = read_csv_rows(resolve_project_path(args.pose_camera_2))
    if len(rows1) != len(rows2):
        print(
            f"ATTENTION: nombre de frames different entre les deux vues ({len(rows1)} vs {len(rows2)}); "
            f"troncature a la plus courte.", file=sys.stderr,
        )
    n_frames = min(len(rows1), len(rows2))

    # Matches extract_motion.py's raw-CSV schema exactly (data_contract.md): frame, time_s,
    # pose_detected, then per-marker x/y/z/visibility/presence. valid/interpolated are
    # row-level fields that smooth_motion.py computes itself downstream -- not duplicated here.
    fields = ["frame", "time_s", "pose_detected"]
    for marker in LANDMARKS:
        fields.extend(f"{marker}_{name}" for name in ("x", "y", "z", "visibility", "presence"))

    output_rows: list[dict[str, object]] = []
    reprojection_errors: list[float] = []
    marker_stats = {m: {"attempted": 0, "triangulated": 0, "valid": 0} for m in LANDMARKS}

    for i in range(n_frames):
        row1, row2 = rows1[i], rows2[i]
        time_s = parse_float(row1.get("time_s"))
        out_row: dict[str, object] = {
            "frame": i,
            "time_s": time_s,
            "pose_detected": int(row1.get("pose_detected") == "1" or row2.get("pose_detected") == "1"),
        }
        for marker in LANDMARKS:
            vis1 = parse_float(row1.get(f"{marker}_visibility"))
            vis2 = parse_float(row2.get(f"{marker}_visibility"))
            x1, y1 = parse_float(row1.get(f"{marker}_x_px")), parse_float(row1.get(f"{marker}_y_px"))
            x2, y2 = parse_float(row2.get(f"{marker}_x_px")), parse_float(row2.get(f"{marker}_y_px"))
            visible_both = (
                all(np.isfinite(v) for v in (vis1, vis2, x1, y1, x2, y2))
                and vis1 >= args.min_visibility and vis2 >= args.min_visibility
            )
            marker_stats[marker]["attempted"] += 1
            if not visible_both:
                out_row.update({
                    f"{marker}_x": "", f"{marker}_y": "", f"{marker}_z": "",
                    f"{marker}_visibility": min(v for v in (vis1, vis2) if np.isfinite(v)) if (np.isfinite(vis1) or np.isfinite(vis2)) else "",
                    f"{marker}_presence": "",
                })
                continue
            point_3d = triangulate_point(p1, p2, (x1, y1), (x2, y2))
            marker_stats[marker]["triangulated"] += 1
            rx1, ry1 = reproject(p1, point_3d)
            rx2, ry2 = reproject(p2, point_3d)
            err1 = float(np.hypot(rx1 - x1, ry1 - y1))
            err2 = float(np.hypot(rx2 - x2, ry2 - y2))
            err = (err1 + err2) / 2.0
            reprojection_errors.append(err)
            is_valid = err <= args.max_reprojection_error_px
            if is_valid:
                marker_stats[marker]["valid"] += 1
            # Points with high reprojection error are kept (not blanked): this stage reports
            # geometry, it does not gate quality. validate_motion.py / the quality report
            # (marker_coverage valid_rate) are where reprojection-based filtering decisions belong.
            out_row.update({
                f"{marker}_x": point_3d[0], f"{marker}_y": point_3d[1], f"{marker}_z": point_3d[2],
                f"{marker}_visibility": min(vis1, vis2),
                f"{marker}_presence": "",
            })
        output_rows.append(out_row)

    output_path = resolve_project_path(args.output)
    write_csv_rows(output_path, fields, output_rows)

    errors = np.array(reprojection_errors) if reprojection_errors else np.array([np.nan])
    quality = {
        "schema_version": 1,
        "source_pose_camera_1": args.pose_camera_1,
        "source_pose_camera_2": args.pose_camera_2,
        "calibration": args.calibration,
        "calibration_warning": calibration.get("warning"),
        "frames": n_frames,
        "reprojection_error_px": {
            "mean": float(np.nanmean(errors)),
            "rms": float(np.sqrt(np.nanmean(errors ** 2))),
            "max": float(np.nanmax(errors)),
            "p95": float(np.nanpercentile(errors, 95)),
            "threshold": args.max_reprojection_error_px,
        },
        "marker_coverage": {
            marker: {
                "attempted_frames": stats["attempted"],
                "triangulated_frames": stats["triangulated"],
                "triangulated_rate": stats["triangulated"] / stats["attempted"] if stats["attempted"] else 0.0,
                "valid_frames": stats["valid"],
                "valid_rate": stats["valid"] / stats["attempted"] if stats["attempted"] else 0.0,
            }
            for marker, stats in marker_stats.items()
        },
        "note": (
            "RMS/max/p95 de reprojection ne valent que ce que vaut la calibration utilisee. "
            "Avec une calibration derivee de fiches techniques (voir calibration_warning), "
            "une faible erreur de reprojection ne prouve PAS une reconstruction 3D metriquement exacte -- "
            "elle prouve seulement une coherence interne entre les deux vues et le modele de camera suppose."
        ),
    }
    quality_path = resolve_project_path(args.quality_output)
    dump_json(quality_path, quality)

    print(f"Frames traitees: {n_frames}")
    print(f"Erreur de reprojection: moyenne={quality['reprojection_error_px']['mean']:.2f}px "
          f"RMS={quality['reprojection_error_px']['rms']:.2f}px max={quality['reprojection_error_px']['max']:.2f}px "
          f"(seuil protocole: {args.max_reprojection_error_px}px)")
    print(f"CSV canonique: {output_path}")
    print(f"Rapport qualite: {quality_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
