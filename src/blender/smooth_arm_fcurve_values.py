"""Low-pass filter the extracted arm F-curve values (presentation demo only).

Uses the same Butterworth design (order, cutoff, zero-phase sosfiltfilt) as
src/smooth_motion.py, applied here to joint-angle F-curve values (radians)
instead of marker-position CSV columns. Run with a Python that has scipy
(e.g. .venv310), not Blender's bundled interpreter -- see
docs/blender/demo_smoothed_disclaimer.md for why this variant exists and
what it must not be used for.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--cutoff-hz", type=float, default=6.0)
    parser.add_argument("--order", type=int, default=4)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    fps = float(data["fps"])
    sos = butter(args.order, args.cutoff_hz / (fps / 2.0), btype="low", output="sos")

    result = {
        "fps": fps,
        "frame_start": data["frame_start"],
        "frame_end": data["frame_end"],
        "filter": {"method": "butterworth", "order": args.order, "cutoff_hz": args.cutoff_hz, "zero_phase": "sosfiltfilt"},
        "channels": {},
    }
    for label, channel in data["channels"].items():
        raw = np.array(channel["values_rad"], dtype=float)
        filtered = sosfiltfilt(sos, raw)
        result["channels"][label] = {
            "bone": channel["bone"],
            "data_path": channel["data_path"],
            "index": channel["index"],
            "values_rad": filtered.tolist(),
            "min_deg_before": channel["min_deg"],
            "max_deg_before": channel["max_deg"],
            "min_deg_after": float(np.degrees(filtered.min())),
            "max_deg_after": float(np.degrees(filtered.max())),
            "max_abs_deviation_deg": float(np.degrees(np.max(np.abs(filtered - raw)))),
        }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result), encoding="utf-8")

    print(f"Filtre Butterworth order={args.order} cutoff={args.cutoff_hz}Hz fps={fps:.6g}")
    for label, channel in result["channels"].items():
        print(
            f"  {label}: avant [{channel['min_deg_before']:.3f}, {channel['max_deg_before']:.3f}] deg -> "
            f"apres [{channel['min_deg_after']:.3f}, {channel['max_deg_after']:.3f}] deg, "
            f"deviation max {channel['max_abs_deviation_deg']:.3f} deg"
        )
    print(f"Sortie: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
