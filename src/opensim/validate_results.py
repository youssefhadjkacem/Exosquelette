"""Validate OpenSim storage files and gate their use by RL or reporting."""

from __future__ import annotations

import argparse
import math
import statistics
import sys
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_ROOT))
from pipeline_utils import dump_json, resolve_project_path  # noqa: E402


def read_storage(path: Path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    end = next(index for index, line in enumerate(lines) if line.strip().lower() == "endheader")
    columns = lines[end + 1].split()
    data = [[float(value) for value in line.split()] for line in lines[end + 2:] if line.strip()]
    if not data or any(len(row) != len(columns) for row in data):
        raise ValueError(f"Format storage invalide: {path}")
    in_degrees = any(line.strip().lower() == "indegrees=yes" for line in lines[: end + 1])
    return columns, data, in_degrees


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ik", default="data/results/opensim/ik_results.mot")
    parser.add_argument("--activations", default=None)
    parser.add_argument("--marker-errors", default=None, help="Storage OpenSim contenant les erreurs de marqueurs en metres.")
    parser.add_argument("--output", default="data/results/opensim/quality.json")
    parser.add_argument("--max-marker-rms-m", type=float, default=0.02)
    parser.add_argument("--max-angular-acc-deg-s2", type=float, default=3000.0)
    parser.add_argument("--max-saturation-rate", type=float, default=0.10)
    args = parser.parse_args(argv)
    failures, report = [], {"schema_version": 1}
    try:
        columns, data, in_degrees = read_storage(resolve_project_path(args.ik))
        times = [row[0] for row in data]
        dt = statistics.median(b - a for a, b in zip(times, times[1:]))
        accelerations = {}
        for index, column in enumerate(columns[1:], 1):
            values = [row[index] for row in data]
            unit_scale = 1.0 if in_degrees else 180.0 / math.pi
            maximum = unit_scale * max(abs((values[i + 1] - 2 * values[i] + values[i - 1]) / (dt * dt)) for i in range(1, len(values) - 1))
            accelerations[column] = maximum
            if maximum > args.max_angular_acc_deg_s2:
                failures.append(f"{column}: acceleration {maximum:.1f} deg/s2")
        report["ik"] = {"rows": len(data), "time_range_s": [times[0], times[-1]], "max_abs_acceleration_deg_s2": accelerations}

        if args.marker_errors:
            error_columns, errors, _ = read_storage(resolve_project_path(args.marker_errors))
            if "marker_error_RMS" in error_columns:
                rms_index = error_columns.index("marker_error_RMS")
                values = [row[rms_index] for row in errors if math.isfinite(row[rms_index])]
            else:
                values = [value for row in errors for value in row[1:] if math.isfinite(value)]
            rms = math.sqrt(statistics.fmean(value * value for value in values))
            report["marker_rms_m"] = rms
            if "marker_error_max" in error_columns:
                max_index = error_columns.index("marker_error_max")
                report["maximum_marker_error_m"] = max(row[max_index] for row in errors)
            if rms > args.max_marker_rms_m:
                failures.append(f"RMS marqueurs {rms:.4f} m")
        else:
            failures.append("RMS marqueurs absente: fournir --marker-errors")

        if args.activations:
            activation_columns, activations, _ = read_storage(resolve_project_path(args.activations))
            saturation = {}
            for index, column in enumerate(activation_columns[1:], 1):
                rate = sum(row[index] >= 0.9999 for row in activations) / len(activations)
                saturation[column] = rate
                if rate > args.max_saturation_rate:
                    failures.append(f"{column}: saturation {rate:.1%}")
            report["activation_saturation_rate"] = saturation
    except (OSError, ValueError, StopIteration) as exc:
        print(f"Validation OpenSim impossible: {exc}", file=sys.stderr)
        return 2

    report["status"] = "PASS" if not failures else "FAIL"
    report["failures"] = failures
    report["thresholds"] = {
        "max_marker_rms_m": args.max_marker_rms_m,
        "max_angular_acc_deg_s2": args.max_angular_acc_deg_s2,
        "max_saturation_rate": args.max_saturation_rate,
    }
    output = resolve_project_path(args.output)
    dump_json(output, report)
    print(f"Qualite OpenSim: {report['status']}")
    for failure in failures:
        print(f"- {failure}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
