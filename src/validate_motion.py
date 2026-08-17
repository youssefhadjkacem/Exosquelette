"""Profile motion data and enforce quality gates before biomechanical analysis."""

from __future__ import annotations

import argparse
import math
import statistics
import sys

from pipeline_utils import coordinate_markers, dump_json, parse_float, read_csv_rows, resolve_project_path


SEGMENTS = (
    ("shoulder", "elbow"), ("elbow", "wrist"),
    ("r_shoulder", "r_elbow"), ("r_elbow", "r_wrist"),
    ("l_shoulder", "l_elbow"), ("l_elbow", "l_wrist"),
)


def coefficient_of_variation(values: list[float]) -> float:
    if len(values) < 2 or statistics.fmean(values) == 0:
        return math.inf
    return statistics.pstdev(values) / statistics.fmean(values)


def analyze(path, max_missing_rate: float, max_segment_cv: float, max_frame_gap: int, required_markers=None) -> dict:
    fieldnames, rows = read_csv_rows(path)
    markers = coordinate_markers(fieldnames)
    if required_markers:
        absent = sorted(set(required_markers) - set(markers))
        if absent:
            raise ValueError(f"Marqueurs requis absents: {', '.join(absent)}")
        markers = {name: markers[name] for name in required_markers}
    if not rows or not markers:
        raise ValueError("CSV vide ou sans triplets de coordonnees 3D.")
    frames = [int(parse_float(row.get("frame"))) for row in rows]
    gaps = [b - a - 1 for a, b in zip(frames, frames[1:]) if b - a > 1]
    non_monotonic = sum(b <= a for a, b in zip(frames, frames[1:]))
    marker_stats = {}
    for marker, axes in markers.items():
        missing = sum(
            not all(math.isfinite(parse_float(row.get(axes[axis]))) for axis in ("x", "y", "z"))
            for row in rows
        )
        marker_stats[marker] = {"missing_frames": missing, "missing_rate": missing / len(rows)}

    segment_stats = {}
    for first, second in SEGMENTS:
        if first not in markers or second not in markers:
            continue
        distances = []
        for row in rows:
            p1 = [parse_float(row.get(markers[first][axis])) for axis in ("x", "y", "z")]
            p2 = [parse_float(row.get(markers[second][axis])) for axis in ("x", "y", "z")]
            if all(math.isfinite(value) for value in [*p1, *p2]):
                distances.append(math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2))))
        segment_stats[f"{first}->{second}"] = {
            "samples": len(distances),
            "mean": statistics.fmean(distances) if distances else None,
            "cv": coefficient_of_variation(distances),
        }

    time_status = "missing"
    inferred_fps = None
    if "time_s" in fieldnames:
        times = [parse_float(row.get("time_s")) for row in rows]
        deltas = [b - a for a, b in zip(times, times[1:]) if math.isfinite(a) and math.isfinite(b)]
        if deltas and all(delta > 0 for delta in deltas):
            time_status = "monotonic"
            inferred_fps = 1.0 / statistics.median(deltas)
        else:
            time_status = "invalid"

    failures = []
    if non_monotonic:
        failures.append(f"{non_monotonic} transitions de frame non monotones")
    if gaps and max(gaps) > max_frame_gap:
        failures.append(f"lacune maximale de {max(gaps)} frames > {max_frame_gap}")
    if time_status == "invalid":
        failures.append("colonne time_s non monotone")
    for marker, stats in marker_stats.items():
        if stats["missing_rate"] > max_missing_rate:
            failures.append(f"{marker}: donnees manquantes {stats['missing_rate']:.1%}")
    for segment, stats in segment_stats.items():
        if stats["cv"] > max_segment_cv:
            failures.append(f"{segment}: variation de longueur CV={stats['cv']:.1%}")

    return {
        "schema_version": 1, "source": str(path),
        "status": "PASS" if not failures else "FAIL",
        "rows": len(rows), "columns": len(fieldnames),
        "frame_range": [min(frames), max(frames)],
        "frame_gap_events": len(gaps), "missing_frames_from_gaps": sum(gaps),
        "maximum_frame_gap": max(gaps, default=0),
        "time_status": time_status, "inferred_fps": inferred_fps,
        "markers": marker_stats, "segments": segment_stats,
        "thresholds": {
            "max_missing_rate": max_missing_rate,
            "max_segment_cv": max_segment_cv,
            "max_frame_gap": max_frame_gap,
        },
        "failures": failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/motion_data_smoothed.csv")
    parser.add_argument("--output", default="data/results/motion_quality.json")
    parser.add_argument("--max-missing-rate", type=float, default=0.02)
    parser.add_argument("--max-segment-cv", type=float, default=0.10)
    parser.add_argument("--max-frame-gap", type=int, default=0)
    parser.add_argument(
        "--required-markers", default=None,
        help="Liste separee par des virgules, ex. r_shoulder,r_elbow,r_wrist.",
    )
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        required = [item.strip() for item in args.required_markers.split(",")] if args.required_markers else None
        report = analyze(
            resolve_project_path(args.input), args.max_missing_rate,
            args.max_segment_cv, args.max_frame_gap, required,
        )
    except (OSError, ValueError) as exc:
        print(f"Validation impossible: {exc}", file=sys.stderr)
        return 2
    output = resolve_project_path(args.output)
    dump_json(output, report)
    print(f"Qualite mouvement: {report['status']}")
    for failure in report["failures"]:
        print(f"- {failure}")
    print(f"Rapport: {output}")
    return 0 if report["status"] == "PASS" or args.report_only else 1


if __name__ == "__main__":
    raise SystemExit(main())
