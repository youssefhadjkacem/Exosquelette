"""Interpolate short pose gaps and low-pass filter continuous valid motion segments."""

from __future__ import annotations

import argparse
import math
import sys

import numpy as np
from scipy.signal import butter, sosfiltfilt

from pipeline_utils import (
    contiguous_ranges, coordinate_markers, parse_float, read_csv_rows,
    resolve_project_path, write_csv_rows,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/motion_data_v2.csv")
    parser.add_argument("--output", default="data/motion_data_smoothed.csv")
    parser.add_argument("--fps", type=float, default=None, help="Obligatoire si time_s est absent.")
    parser.add_argument("--cutoff-hz", type=float, default=6.0)
    parser.add_argument("--order", type=int, default=4)
    parser.add_argument("--max-gap-frames", type=int, default=5)
    parser.add_argument("--min-visibility", type=float, default=0.5)
    return parser


def interpolate_short_gaps(values: np.ndarray, max_gap: int) -> tuple[np.ndarray, np.ndarray]:
    result = values.copy()
    interpolated = np.zeros(len(values), dtype=bool)
    finite = np.isfinite(result)
    index = 0
    while index < len(result):
        if finite[index]:
            index += 1
            continue
        start = index
        while index < len(result) and not finite[index]:
            index += 1
        stop = index
        if start > 0 and stop < len(result) and stop - start <= max_gap:
            result[start:stop] = np.interp(
                np.arange(start, stop), [start - 1, stop], [result[start - 1], result[stop]]
            )
            interpolated[start:stop] = True
    return result, interpolated


def filter_valid_segments(values: np.ndarray, fps: float, cutoff: float, order: int) -> np.ndarray:
    sos = butter(order, cutoff / (fps / 2.0), btype="low", output="sos")
    result = values.copy()
    for start, stop in contiguous_ranges(np.isfinite(values).tolist()):
        try:
            result[start:stop] = sosfiltfilt(sos, values[start:stop])
        except ValueError:
            # Segments shorter than scipy's padding requirement stay unfiltered.
            pass
    return result


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    fieldnames, source_rows = read_csv_rows(resolve_project_path(args.input))
    if not source_rows or "frame" not in fieldnames:
        print("Le CSV doit contenir au moins une ligne et une colonne frame.", file=sys.stderr)
        return 2

    frames = [int(parse_float(row["frame"])) for row in source_rows]
    by_frame = {frame: row for frame, row in zip(frames, source_rows)}
    full_frames = list(range(min(frames), max(frames) + 1))

    fps = args.fps
    if "time_s" in fieldnames:
        pairs = [(parse_float(row["frame"]), parse_float(row.get("time_s"))) for row in source_rows]
        deltas = [
            (tb - ta) / (fb - fa) for (fa, ta), (fb, tb) in zip(pairs, pairs[1:])
            if fb > fa and all(math.isfinite(v) for v in (ta, tb))
        ]
        if deltas:
            fps = 1.0 / float(np.median(deltas))
    if not fps or fps <= 0:
        print("FPS introuvable. Fournissez --fps ou une colonne time_s valide.", file=sys.stderr)
        return 2
    if not 0 < args.cutoff_hz < fps / 2:
        print("cutoff-hz doit etre compris entre 0 et la frequence de Nyquist.", file=sys.stderr)
        return 2

    markers = coordinate_markers(fieldnames)
    if not markers:
        print("Aucun triplet *_x/*_y/*_z trouve.", file=sys.stderr)
        return 2

    output_fields = list(fieldnames)
    for required in ("time_s", "pose_detected", "valid", "interpolated"):
        if required not in output_fields:
            output_fields.append(required)
    rows: list[dict[str, object]] = []
    for frame in full_frames:
        row: dict[str, object] = dict(by_frame.get(frame, {}))
        row["frame"] = frame
        row["time_s"] = frame / fps
        row["pose_detected"] = row.get("pose_detected", int(frame in by_frame))
        rows.append(row)

    any_interpolated = np.zeros(len(rows), dtype=bool)
    for marker, axes in markers.items():
        visibility = np.array([parse_float(row.get(f"{marker}_visibility", 1.0)) for row in rows])
        visible = np.isfinite(visibility) & (visibility >= args.min_visibility)
        for axis in ("x", "y", "z"):
            column = axes[axis]
            values = np.array([parse_float(row.get(column)) for row in rows], dtype=float)
            values[~visible] = np.nan
            values, interpolated = interpolate_short_gaps(values, args.max_gap_frames)
            values = filter_valid_segments(values, fps, args.cutoff_hz, args.order)
            any_interpolated |= interpolated
            for index, value in enumerate(values):
                rows[index][column] = "" if not math.isfinite(value) else value

    for index, row in enumerate(rows):
        valid = all(
            math.isfinite(parse_float(row.get(column)))
            for axes in markers.values() for column in axes.values()
        )
        row["valid"] = int(valid)
        row["interpolated"] = int(any_interpolated[index])

    output_path = resolve_project_path(args.output)
    write_csv_rows(output_path, output_fields, rows)
    valid_count = sum(int(row["valid"]) for row in rows)
    print(f"Lissage: {len(rows)} frames, {valid_count} entierement valides, fps={fps:.6g}")
    print(f"Sortie: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
