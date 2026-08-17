"""Convert calibrated motion CSV data to OpenSim TRC without changing time."""

from __future__ import annotations

import argparse
import math
import statistics
import sys

import numpy as np

from pipeline_utils import load_json, parse_float, read_csv_rows, resolve_project_path


MARKER_MAP = {
    "right": (("r_shoulder", "r_acromion"), ("r_elbow", "r_humerus_epicondyle"), ("r_wrist", "r_radius_styloid")),
    "left": (("l_shoulder", "l_acromion"), ("l_elbow", "l_humerus_epicondyle"), ("l_wrist", "l_radius_styloid")),
    "legacy-right": (("shoulder", "r_acromion"), ("elbow", "r_humerus_epicondyle"), ("wrist", "r_radius_styloid")),
}


def transform_point(row: dict[str, str], source: str, matrix: np.ndarray, scale: float) -> list[float]:
    point = np.array([parse_float(row.get(f"{source}_x")), parse_float(row.get(f"{source}_y")), parse_float(row.get(f"{source}_z")), 1.0])
    if not np.isfinite(point).all():
        return [math.nan, math.nan, math.nan]
    return ((matrix @ point)[:3] * scale).tolist()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/motion_data_smoothed.csv")
    parser.add_argument("--output", default="data/motion_data.trc")
    parser.add_argument("--calibration", default="config/calibration.json")
    parser.add_argument("--side", choices=tuple(MARKER_MAP), default="right")
    parser.add_argument("--allow-unvalidated-calibration", action="store_true")
    parser.add_argument("--allow-missing", action="store_true")
    args = parser.parse_args(argv)
    input_path, output_path = resolve_project_path(args.input), resolve_project_path(args.output)
    try:
        calibration = load_json(resolve_project_path(args.calibration))
        fieldnames, rows = read_csv_rows(input_path)
    except (OSError, ValueError) as exc:
        print(f"Entree invalide: {exc}", file=sys.stderr)
        return 2
    if not calibration.get("analysis_valid", False) and not args.allow_unvalidated_calibration:
        print("Calibration non validee. --allow-unvalidated-calibration est reserve a la visualisation.", file=sys.stderr)
        return 1
    scale = calibration.get("scale_mm_per_unit")
    matrix = np.asarray(calibration.get("transform_4x4"), dtype=float)
    if not isinstance(scale, (int, float)) or scale <= 0 or matrix.shape != (4, 4):
        print("La calibration doit definir scale_mm_per_unit>0 et transform_4x4 (4x4).", file=sys.stderr)
        return 2
    mapping = MARKER_MAP[args.side]
    required = [f"{source}_{axis}" for source, _ in mapping for axis in ("x", "y", "z")]
    missing_columns = [column for column in required if column not in fieldnames]
    if missing_columns:
        print(f"Colonnes absentes: {', '.join(missing_columns)}", file=sys.stderr)
        return 2
    times = [parse_float(row.get("time_s")) for row in rows]
    if not all(math.isfinite(value) for value in times):
        print("time_s est obligatoire et fini pour chaque frame.", file=sys.stderr)
        return 2
    deltas = [b - a for a, b in zip(times, times[1:])]
    if not deltas or any(delta <= 0 for delta in deltas):
        print("time_s doit etre strictement croissant.", file=sys.stderr)
        return 2
    fps = 1.0 / statistics.median(deltas)
    transformed = [[transform_point(row, source, matrix, float(scale)) for source, _ in mapping] for row in rows]
    missing_count = sum(not all(math.isfinite(v) for v in point) for frame in transformed for point in frame)
    if missing_count and not args.allow_missing:
        print(f"Conversion bloquee: {missing_count} positions manquantes.", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(f"PathFileType\t4\t(X/Y/Z)\t{output_path.name}\n")
        stream.write("DataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits\tOrigDataRate\tOrigDataStartFrame\tOrigNumFrames\n")
        stream.write(f"{fps:.8g}\t{fps:.8g}\t{len(rows)}\t{len(mapping)}\tmm\t{fps:.8g}\t1\t{len(rows)}\n")
        stream.write("Frame#\tTime\t" + "\t\t\t".join(target for _, target in mapping) + "\t\t\n")
        coordinates = [value for index in range(1, len(mapping) + 1) for value in (f"X{index}", f"Y{index}", f"Z{index}")]
        stream.write("\t\t" + "\t".join(coordinates) + "\n\n")
        for row, time_s, points in zip(rows, times, transformed):
            frame_number = int(parse_float(row.get("frame"))) + 1
            values = ["nan" if not math.isfinite(value) else f"{value:.6f}" for point in points for value in point]
            stream.write(f"{frame_number}\t{time_s:.8f}\t" + "\t".join(values) + "\n")
    print(f"TRC: {output_path}")
    print(f"Frames={len(rows)}, marqueurs={len(mapping)}, fps={fps:.6g}, manquants={missing_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
