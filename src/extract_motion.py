"""Extract a timestamped, quality-aware MediaPipe pose stream from a video."""

from __future__ import annotations

import argparse
import sys

from pipeline_utils import resolve_project_path, write_csv_rows


LANDMARKS = (
    "r_shoulder", "r_elbow", "r_wrist",
    "l_shoulder", "l_elbow", "l_wrist",
    "r_hip", "l_hip",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", default="data/videos/video_principale.mp4")
    parser.add_argument("--output", default="data/motion_data_v2.csv")
    parser.add_argument("--show", action="store_true", help="Afficher la detection pendant l'extraction.")
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
    if not fps or fps <= 0:
        capture.release()
        print("FPS video invalide; impossible de construire la base temporelle.", file=sys.stderr)
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
        fields.extend(f"{marker}_{name}" for name in ("x", "y", "z", "visibility", "presence"))

    rows: list[dict[str, object]] = []
    detected = 0
    frame_number = 0
    drawing = mp.solutions.drawing_utils
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
                            f"{marker}_x": point.x,
                            f"{marker}_y": point.y,
                            f"{marker}_z": point.z,
                            f"{marker}_visibility": point.visibility,
                            f"{marker}_presence": getattr(point, "presence", ""),
                        })
                    if args.show:
                        drawing.draw_landmarks(frame, result.pose_landmarks, pose_module.POSE_CONNECTIONS)
                rows.append(row)
                if args.show:
                    cv2.imshow("Motion Capture", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                frame_number += 1
    finally:
        capture.release()
        if args.show:
            cv2.destroyAllWindows()

    write_csv_rows(output_path, fields, rows)
    coverage = detected / len(rows) if rows else 0.0
    print(f"Video: {len(rows)} frames a {fps:.6g} fps")
    print(f"Pose detectee: {detected}/{len(rows)} ({coverage:.1%})")
    print(f"CSV canonique: {output_path}")
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
