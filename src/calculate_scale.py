"""Estimate a scale from measured limb lengths and refuse inconsistent monocular calibration."""

from __future__ import annotations

import argparse
import math
import statistics

from pipeline_utils import dump_json, parse_float, read_csv_rows, resolve_project_path


def distances(rows, first: str, second: str) -> list[float]:
    values = []
    for row in rows:
        p1 = [parse_float(row.get(f"{first}_{axis}")) for axis in "xyz"]
        p2 = [parse_float(row.get(f"{second}_{axis}")) for axis in "xyz"]
        if all(math.isfinite(value) for value in [*p1, *p2]):
            values.append(math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2))))
    return values


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/motion_data_smoothed.csv")
    parser.add_argument("--output", default="config/calibration.json")
    parser.add_argument("--side", choices=("right", "left", "legacy-right"), default="right")
    parser.add_argument("--upper-arm-mm", type=float, required=True)
    parser.add_argument("--forearm-mm", type=float, required=True)
    parser.add_argument("--max-segment-cv", type=float, default=0.10)
    parser.add_argument("--max-scale-disagreement", type=float, default=0.10)
    parser.add_argument("--metric-3d-source", action="store_true", help="Confirmer une source stereo/RGB-D metrique.")
    parser.add_argument(
        "--confirm-opensim-frame", action="store_true",
        help="Confirmer que les coordonnees sont deja exprimees dans le repere OpenSim.",
    )
    args = parser.parse_args(argv)
    _, rows = read_csv_rows(resolve_project_path(args.input))
    prefix = "" if args.side == "legacy-right" else ("r_" if args.side == "right" else "l_")
    upper = distances(rows, f"{prefix}shoulder", f"{prefix}elbow")
    forearm = distances(rows, f"{prefix}elbow", f"{prefix}wrist")
    if len(upper) < 2 or len(forearm) < 2:
        raise SystemExit("Pas assez de segments valides pour calculer l'echelle.")
    upper_scale = args.upper_arm_mm / statistics.median(upper)
    forearm_scale = args.forearm_mm / statistics.median(forearm)
    scale = statistics.fmean((upper_scale, forearm_scale))
    disagreement = abs(upper_scale - forearm_scale) / scale
    upper_cv = statistics.pstdev(upper) / statistics.fmean(upper)
    forearm_cv = statistics.pstdev(forearm) / statistics.fmean(forearm)
    valid = (
        args.metric_3d_source and args.confirm_opensim_frame
        and disagreement <= args.max_scale_disagreement
        and max(upper_cv, forearm_cv) <= args.max_segment_cv
    )
    report = {
        "schema_version": 1,
        "source_space": "metric_3d" if args.metric_3d_source else "monocular_or_unknown",
        "analysis_valid": valid,
        "scale_mm_per_unit": scale,
        "transform_4x4": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
        "calibration_method": "anthropometric_segment_lengths",
        "diagnostics": {
            "upper_arm_scale": upper_scale, "forearm_scale": forearm_scale,
            "scale_disagreement": disagreement,
            "upper_arm_cv": upper_cv, "forearm_cv": forearm_cv,
        },
        "thresholds": {
            "max_scale_disagreement": args.max_scale_disagreement,
            "max_segment_cv": args.max_segment_cv,
        },
    }
    output = resolve_project_path(args.output)
    dump_json(output, report)
    print(f"Calibration: {'PASS' if valid else 'FAIL'}; scale={scale:.3f} mm/unite")
    print(f"Desaccord des segments={disagreement:.1%}; CV max={max(upper_cv, forearm_cv):.1%}")
    print(f"Fichier: {output}")
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
