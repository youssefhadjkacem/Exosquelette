"""Detect 2D pixel pose landmarks in a single camera view (multiview step B).

Unlike extract_motion.py, this deliberately keeps MediaPipe's normalized (x,y)
scaled to real pixel coordinates and DROPS its z entirely: z from a single
monocular view is MediaPipe's own rough depth guess, not a measurement, and
triangulate_multiview.py (step D) recovers real depth from the two-camera
geometry instead. Run once per camera; the two output CSVs are the inputs to
triangulate_multiview.py.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def write_csv_rows(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    import csv
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


LANDMARKS = (
    "r_shoulder", "r_elbow", "r_wrist",
    "l_shoulder", "l_elbow", "l_wrist",
    "r_hip", "l_hip",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-detection-confidence", type=float, default=0.5)
    parser.add_argument("--min-tracking-confidence", type=float, default=0.5)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        import cv2
        import mediapipe as mp
    except ImportError as exc:
        print(
            "Dependance absente. Activez .venv310 puis installez requirements-py310.txt.\n"
            f"Detail: {exc}", file=sys.stderr,
        )
        return 2

    video_path = resolve_project_path(args.video)
    output_path = resolve_project_path(args.output)
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        print(f"Impossible d'ouvrir la video: {video_path}", file=sys.stderr)
        return 2

    fps = float(capture.get(cv2.CAP_PROP_FPS))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if not fps or fps <= 0 or not width or not height:
        capture.release()
        print("FPS ou resolution video invalide.", file=sys.stderr)
        return 2

    pose_module = mp.solutions.pose
    landmark_ids = {
        "r_shoulder": pose_module.PoseLandmark.RIGHT_SHOULDER,
        "r_elbow": pose_module.PoseLandmark.RIGHT_ELBOW,
        "r_wrist": pose_module.PoseLandmark.RIGHT_WRIST,
        "l_shoulder": pose_module.PoseLandmark.LEFT_SHOULDER,
        "l_elbow": pose_module.PoseLandmark.LEFT_ELBOW,
        "l_wrist": pose_module.PoseLandmark.LEFT_WRIST,
        "r_hip": pose_module.PoseLandmark.RIGHT_HIP,
        "l_hip": pose_module.PoseLandmark.LEFT_HIP,
    }
    fields = ["frame", "time_s", "pose_detected"]
    for marker in LANDMARKS:
        fields.extend(f"{marker}_{name}" for name in ("x_px", "y_px", "visibility", "presence"))

    rows: list[dict[str, object]] = []
    detected = 0
    frame_number = 0
    try:
        with pose_module.Pose(
            min_detection_confidence=args.min_detection_confidence,
            min_tracking_confidence=args.min_tracking_confidence,
        ) as pose:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                result = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                row: dict[str, object] = {
                    "frame": frame_number,
                    "time_s": frame_number / fps,
                    "pose_detected": int(result.pose_landmarks is not None),
                }
                if result.pose_landmarks:
                    detected += 1
                    for marker, landmark_id in landmark_ids.items():
                        point = result.pose_landmarks.landmark[landmark_id]
                        row.update({
                            f"{marker}_x_px": point.x * width,
                            f"{marker}_y_px": point.y * height,
                            f"{marker}_visibility": point.visibility,
                            f"{marker}_presence": getattr(point, "presence", ""),
                        })
                rows.append(row)
                frame_number += 1
    finally:
        capture.release()

    write_csv_rows(output_path, fields, rows)
    coverage = detected / len(rows) if rows else 0.0
    print(f"Video: {video_path.name}: {len(rows)} frames a {fps:.6g} fps, resolution {width}x{height}")
    print(f"Pose detectee: {detected}/{len(rows)} ({coverage:.1%})")
    print(f"CSV 2D (pixels): {output_path}")
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
