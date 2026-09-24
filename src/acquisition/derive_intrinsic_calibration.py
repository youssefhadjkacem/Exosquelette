"""Derive an APPROXIMATE stereo calibration from phone spec sheets, not a checkerboard.

This is a placeholder calibration for software development only. It lets the
multiview pipeline (2D detection -> triangulation -> canonical CSV) be built
and exercised end-to-end before a real checkerboard capture exists. Every
number it produces is downstream of manufacturer marketing specs and visual
guesses, not measurement -- see the "warning" field the output always carries,
and docs/data_contract.md / data_v3 session notes for the deviation record.

Key derivation (focal length in pixels):
    f_pixels = equivalent_focal_length_mm * video_width_px / (43.2666 * 0.8)

This uses only the 35mm-equivalent focal length (a reliable, Apple-published
number) and the assumption that 1080p video uses the camera's full sensor
WIDTH (cropped only in height for 16:9, not resampled/cropped horizontally).
The physical sensor size class ("1/1.56\"" etc.) algebraically cancels out of
this formula -- it is reported for reference/cross-checking only and does not
change the result. iOS's actual 1080p crop/binning behaviour is not publicly
documented, so this is the single biggest source of unquantified error here.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def dump_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


FULL_FRAME_DIAGONAL_MM = 43.2666  # 36x24mm reference sensor, CIPA equivalent-focal-length convention
NATIVE_ASPECT_WIDTH_RATIO = 0.8  # width/diagonal for a 4:3 native sensor


def sensor_diagonal_mm_from_inch_class(inch_denominator: float) -> float:
    """Widely-used rule-of-thumb for '1/N inch' video-sensor notation. Approximate."""
    return 16.0 / inch_denominator


def focal_length_px(equivalent_focal_mm: float, video_width_px: int) -> float:
    return equivalent_focal_mm * video_width_px / (FULL_FRAME_DIAGONAL_MM * NATIVE_ASPECT_WIDTH_RATIO)


def camera_pose(azimuth_deg: float, distance_m: float, height_m: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """World-to-camera pose for a level camera (no roll/pitch) pointed at a fixed target,
    placed on a circle of `distance_m` around the origin at azimuth `azimuth_deg`
    (0 deg = facing the subject head-on, 90 deg = directly to the subject's side)."""
    az = math.radians(azimuth_deg)
    cam_pos = np.array([distance_m * math.cos(az), distance_m * math.sin(az), height_m])
    target = np.array([0.0, 0.0, height_m])
    forward = target - cam_pos
    forward = forward / np.linalg.norm(forward)
    world_up = np.array([0.0, 0.0, 1.0])
    right = np.cross(forward, world_up)
    right = right / np.linalg.norm(right)
    down = np.cross(forward, right)
    rotation = np.stack([right, down, forward], axis=0)
    translation = -rotation @ cam_pos
    return cam_pos, rotation, translation


def build_camera(name: str, role: str, equivalent_focal_mm: float, inch_class: float, pixel_um: float,
                  video_w: int, video_h: int, azimuth_deg: float, distance_m: float, height_m: float,
                  megapixels_reported: float) -> dict:
    f_px = focal_length_px(equivalent_focal_mm, video_w)
    diag_mm = sensor_diagonal_mm_from_inch_class(inch_class)
    width_mm = diag_mm * NATIVE_ASPECT_WIDTH_RATIO
    implied_native_width_px = width_mm * 1000.0 / pixel_um
    reported_native_width_px = math.sqrt(megapixels_reported * 1e6 * 4.0 / 3.0)
    sensor_class_consistency_error = abs(implied_native_width_px - reported_native_width_px) / reported_native_width_px

    position, rotation, translation = camera_pose(azimuth_deg, distance_m, height_m)

    return {
        "name": name,
        "role": role,
        "source_spec": {
            "equivalent_focal_length_mm": equivalent_focal_mm,
            "sensor_inch_class": f"1/{inch_class}\"",
            "pixel_pitch_um": pixel_um,
            "reported_main_camera_megapixels": megapixels_reported,
        },
        "intrinsic_matrix": [
            [f_px, 0.0, video_w / 2.0],
            [0.0, f_px, video_h / 2.0],
            [0.0, 0.0, 1.0],
        ],
        "distortion_coefficients": [0.0, 0.0, 0.0, 0.0, 0.0],
        "image_size": [video_w, video_h],
        "sensor_class_cross_check": {
            "sensor_diagonal_mm_from_inch_class": diag_mm,
            "sensor_width_mm_from_inch_class": width_mm,
            "implied_native_width_px_from_pixel_pitch": implied_native_width_px,
            "apple_reported_native_width_px_from_megapixels": reported_native_width_px,
            "relative_error": sensor_class_consistency_error,
            "note": "Does NOT feed into intrinsic_matrix (which cancels sensor size out); "
                    "shown only as a plausibility check on the inch-class approximation.",
        },
        "extrinsic": {
            "azimuth_deg": azimuth_deg,
            "distance_to_subject_m": distance_m,
            "height_m": height_m,
            "world_position_m": position.tolist(),
            "rotation_world_to_camera": rotation.tolist(),
            "translation_world_to_camera_m": translation.tolist(),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/sessions/session_capture_stereo_test/calibration/stereo_calibration.json")
    parser.add_argument("--video-width", type=int, default=1920)
    parser.add_argument("--video-height", type=int, default=1080)
    parser.add_argument("--subject-stature-m", type=float, default=1.60)
    parser.add_argument("--shoulder-height-ratio", type=float, default=0.818, help="Drillis & Contini")
    parser.add_argument("--distance-to-subject-m", type=float, default=1.8,
                         help="Rough visual estimate (door-height cross-check), not measured.")
    parser.add_argument("--camera1-azimuth-deg", type=float, default=90.0)
    parser.add_argument("--camera2-azimuth-deg", type=float, default=5.0,
                         help="Midpoint of the achieved ~0-10 deg range (protocol target was 35 deg).")
    args = parser.parse_args(argv)

    height_m = args.subject_stature_m * args.shoulder_height_ratio

    camera_1 = build_camera(
        name="camera_1", role="right_lateral_view",
        equivalent_focal_mm=26.0, inch_class=1.56, pixel_um=1.0,
        video_w=args.video_width, video_h=args.video_height,
        azimuth_deg=args.camera1_azimuth_deg, distance_m=args.distance_to_subject_m, height_m=height_m,
        megapixels_reported=48.0,
    )
    camera_2 = build_camera(
        name="camera_2", role="front_oblique_view",
        equivalent_focal_mm=26.0, inch_class=1.65, pixel_um=1.7,
        video_w=args.video_width, video_h=args.video_height,
        azimuth_deg=args.camera2_azimuth_deg, distance_m=args.distance_to_subject_m, height_m=height_m,
        megapixels_reported=12.0,
    )

    R1 = np.array(camera_1["extrinsic"]["rotation_world_to_camera"])
    t1 = np.array(camera_1["extrinsic"]["translation_world_to_camera_m"])
    R2 = np.array(camera_2["extrinsic"]["rotation_world_to_camera"])
    t2 = np.array(camera_2["extrinsic"]["translation_world_to_camera_m"])
    R_rel = R2 @ R1.T
    T_rel = t2 - R_rel @ t1

    calibration = {
        "schema_version": 1,
        "warning": (
            "APPROXIMATION NON MESUREE. Calibration derivee des fiches techniques constructeur "
            "(focale equivalente 35mm publiee par Apple) et d'hypotheses geometriques visuelles, "
            "PAS d'une calibration damier. Precision non garantie. La plus grosse incertitude non "
            "quantifiee est le facteur de crop/binning reel utilise par iOS en mode video 1080p "
            "(non documente publiquement par Apple) -- on suppose ici que la largeur video utilise "
            "toute la largeur du capteur, sans recadrage horizontal. La distance camera-sujet et les "
            "azimuts sont des estimations visuelles/documentees, pas des mesures. A remplacer par "
            "une vraie calibration damier (cv2.calibrateCamera + cv2.stereoCalibrate) des que possible."
        ),
        "session_id": "v3_test_20260825",
        "derivation_method": "phone_spec_sheet_plus_visual_geometry_estimate",
        "world_frame_convention": (
            "Origine au point de reference du sujet/de la tache (hauteur epaule estimee). "
            "Azimut 0 deg = camera face au sujet ; 90 deg = camera directement sur le cote. "
            "Cameras supposees de niveau (roulis/tangage nuls), a la meme hauteur -- non verifie."
        ),
        "cameras": [camera_1, camera_2],
        "relative_pose_camera1_to_camera2": {
            "rotation": R_rel.tolist(),
            "translation_m": T_rel.tolist(),
            "baseline_m": float(np.linalg.norm(T_rel)),
        },
    }

    output = resolve_project_path(args.output)
    dump_json(output, calibration)
    print(f"Calibration approximative ecrite: {output}")
    print(f"f_pixels (identique pour les 2 cameras): {camera_1['intrinsic_matrix'][0][0]:.2f} px")
    print(f"baseline estimee camera_1<->camera_2: {calibration['relative_pose_camera1_to_camera2']['baseline_m']:.3f} m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
