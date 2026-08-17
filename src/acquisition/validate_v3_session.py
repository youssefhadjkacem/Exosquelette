"""Validate a V3 acquisition template or a completed two-camera session."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def finite_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def validate_measurement(
    value: object, name: str, bounds: dict, pending: list[str], failures: list[str]
) -> None:
    measured = finite_number(value)
    if measured is None:
        pending.append(name)
        return
    if not float(bounds["minimum"]) <= measured <= float(bounds["maximum"]):
        failures.append(
            f"{name}: {measured} outside [{bounds['minimum']}, {bounds['maximum']}]"
        )


def analyze(protocol: dict, session: dict, require_capture: bool = False) -> dict:
    failures: list[str] = []
    pending: list[str] = []
    required = protocol["required_measurements"]
    participant = session.get("participant", {})
    task = session.get("task", {})
    values = {
        "participant_stature_m": participant.get("stature_m"),
        "participant_mass_kg": participant.get("mass_kg"),
        "right_upper_arm_length_m": participant.get("right_upper_arm_length_m"),
        "right_forearm_length_m": participant.get("right_forearm_length_m"),
        "iron_mass_kg": task.get("iron_mass_kg"),
        "table_height_m": task.get("table_height_m"),
    }
    for name, bounds in required.items():
        validate_measurement(values.get(name), name, bounds, pending, failures)

    cycles = finite_number(task.get("complete_cycles_recorded"))
    if cycles is None:
        pending.append("complete_cycles_recorded")
    elif cycles < int(protocol["minimum_complete_cycles"]):
        failures.append(
            f"complete_cycles_recorded: {cycles:g} < {protocol['minimum_complete_cycles']}"
        )

    cameras = session.get("cameras")
    if not isinstance(cameras, list) or len(cameras) != int(protocol["capture"]["camera_count"]):
        failures.append("exactly two camera records are required")
        cameras = []
    expected_roles = {
        key: value["role"] for key, value in protocol["camera_layout"].items()
    }
    camera_ids = [str(camera.get("camera_id", "unknown")) for camera in cameras]
    if len(set(camera_ids)) != len(camera_ids) or set(camera_ids) != set(expected_roles):
        failures.append("camera records must contain camera_1 and camera_2 exactly once")
    fps_values, durations, video_paths = [], [], []
    sync_start_times, sync_end_times = [], []
    for camera in cameras:
        camera_id = str(camera.get("camera_id", "unknown"))
        if camera_id not in expected_roles:
            failures.append(f"{camera_id}: camera_id not declared by protocol")
            continue
        if camera.get("role") != expected_roles[camera_id]:
            failures.append(f"{camera_id}: incorrect camera role")
        for field in ("video", "calibration_file"):
            value = camera.get(field)
            if not value:
                pending.append(f"{camera_id}.{field}")
            elif not resolve(str(value)).is_file():
                failures.append(f"{camera_id}.{field}: file not found: {value}")
            elif field == "video":
                video_paths.append(resolve(str(value)).resolve())
        fps = finite_number(camera.get("fps"))
        duration = finite_number(camera.get("duration_s"))
        resolution = camera.get("resolution")
        if fps is None:
            pending.append(f"{camera_id}.fps")
        elif fps <= 0:
            failures.append(f"{camera_id}.fps must be positive")
        else:
            fps_values.append(fps)
        if duration is None:
            pending.append(f"{camera_id}.duration_s")
        elif duration <= 0:
            failures.append(f"{camera_id}.duration_s must be positive")
        else:
            durations.append(duration)
        if not (
            isinstance(resolution, list) and len(resolution) == 2
            and all(finite_number(value) is not None for value in resolution)
        ):
            pending.append(f"{camera_id}.resolution")
        else:
            minimum = protocol["capture"]["minimum_resolution"]
            if int(resolution[0]) < int(minimum[0]) or int(resolution[1]) < int(minimum[1]):
                failures.append(f"{camera_id}.resolution below {minimum[0]}x{minimum[1]}")
        for field, collection in (
            ("sync_event_start_frame", sync_start_times),
            ("sync_event_end_frame", sync_end_times),
        ):
            frame = finite_number(camera.get(field))
            if frame is None:
                pending.append(f"{camera_id}.{field}")
            elif frame < 0:
                failures.append(f"{camera_id}.{field} must be non-negative")
            elif fps is not None and fps > 0:
                collection.append(frame / fps)
        if not camera.get("all_required_landmarks_visible", False):
            pending.append(f"{camera_id}.all_required_landmarks_visible")

    gates = protocol["quality_gates"]
    if len(fps_values) == 2 and abs(fps_values[0] - fps_values[1]) > float(gates["maximum_camera_fps_difference"]):
        failures.append("camera FPS difference exceeds protocol limit")
    if len(durations) == 2 and abs(durations[0] - durations[1]) > float(gates["maximum_duration_difference_s"]):
        failures.append("camera duration difference exceeds protocol limit")
    if len(video_paths) == 2 and video_paths[0] == video_paths[1]:
        failures.append("camera videos must be two distinct files")
    maximum_sync_error_s = float(protocol["capture"]["maximum_sync_error_ms"]) / 1000.0
    if len(sync_start_times) == 2 and abs(sync_start_times[0] - sync_start_times[1]) > maximum_sync_error_s:
        failures.append("start synchronization error exceeds protocol limit")
    if len(sync_end_times) == 2 and abs(sync_end_times[0] - sync_end_times[1]) > maximum_sync_error_s:
        failures.append("end synchronization error exceeds protocol limit")

    checklist = session.get("checklist", {})
    for item in (
        "participant_consent_recorded", "metric_reference_visible", "checkerboard_recorded",
        "camera_tripods_locked", "lighting_stable", "start_and_end_sync_events_recorded",
    ):
        if not checklist.get(item, False):
            pending.append(f"checklist.{item}")

    pending = sorted(set(pending))
    if failures:
        status = "FAIL"
    elif pending:
        status = "PREPARED_AWAITING_CAPTURE"
    else:
        status = "READY_FOR_3D_RECONSTRUCTION"
    if require_capture and status != "READY_FOR_3D_RECONSTRUCTION":
        failures.append("completed capture is required")
        status = "FAIL"
    return {
        "schema_version": 1,
        "protocol_id": protocol["protocol_id"],
        "session_id": session.get("session_id"),
        "status": status,
        "ready_for_3d_reconstruction": status == "READY_FOR_3D_RECONSTRUCTION",
        "opensim_allowed": False,
        "rl_scientific_allowed": False,
        "pending": pending,
        "failures": failures,
        "note": "OpenSim and scientific RL require downstream 3D and external-load validation.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", default="config/acquisition/v3_session.example.json")
    parser.add_argument("--protocol", default="config/acquisition/v3_protocol.json")
    parser.add_argument("--output", default="data/results/acquisition_v3_readiness.json")
    parser.add_argument("--require-capture", action="store_true")
    args = parser.parse_args(argv)
    try:
        protocol = json.loads(resolve(args.protocol).read_text(encoding="utf-8"))
        session = json.loads(resolve(args.session).read_text(encoding="utf-8"))
        report = analyze(protocol, session, args.require_capture)
        output = resolve(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Validation V3 impossible: {exc}", file=sys.stderr)
        return 2
    print(f"Acquisition V3: {report['status']}")
    print(f"Elements en attente: {len(report['pending'])}")
    for failure in report["failures"]:
        print(f"- {failure}")
    print(f"Rapport: {output}")
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
