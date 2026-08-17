"""Generate a bounded synthetic ironing target for software-only RL development."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def generate(generator: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    duration = float(generator["duration_s"])
    sample_rate = float(generator["sample_rate_hz"])
    frequency = float(generator["cycle_frequency_hz"])
    if duration <= 0 or sample_rate <= 0 or frequency <= 0:
        raise ValueError("duration, sample rate and cycle frequency must be positive")
    count = int(round(duration * sample_rate)) + 1
    time = np.linspace(0.0, duration, count)
    phase = 2.0 * math.pi * frequency * time
    shoulder = (
        float(generator["shoulder_center_deg"])
        + float(generator["shoulder_amplitude_deg"]) * np.sin(phase)
        + 0.12 * float(generator["shoulder_amplitude_deg"]) * np.sin(2.0 * phase)
    )
    elbow = (
        float(generator["elbow_center_deg"])
        + float(generator["elbow_amplitude_deg"])
        * np.sin(phase + math.radians(float(generator["elbow_phase_deg"])))
    )
    return time, shoulder, elbow


def write_mot(path: Path, time: np.ndarray, shoulder: np.ndarray, elbow: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "synthetic_ironing_target_v1",
        f"nRows={len(time)}",
        "nColumns=3",
        "inDegrees=yes",
        "endheader",
        "time\tr_shoulder_elev\tr_elbow_flex",
    ]
    rows = [
        f"{t:.6f}\t{s:.8f}\t{e:.8f}"
        for t, s, e in zip(time, shoulder, elbow)
    ]
    path.write_text("\n".join(header + rows) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/rl/exploratory_sandbox_v1.json")
    args = parser.parse_args(argv)
    try:
        config = json.loads(resolve(args.config).read_text(encoding="utf-8"))
        time, shoulder, elbow = generate(config["target_generator"])
        target_path = resolve(config["target"])
        write_mot(target_path, time, shoulder, elbow)
        report = {
            "schema_version": 1,
            "status": "SYNTHETIC_SOFTWARE_ONLY",
            "sandbox_id": config["sandbox_id"],
            "target": str(target_path),
            "samples": len(time),
            "duration_s": float(time[-1]),
            "cycles": float(config["target_generator"]["cycle_frequency_hz"]) * float(time[-1]),
            "ranges_deg": {
                "r_shoulder_elev": [float(np.min(shoulder)), float(np.max(shoulder))],
                "r_elbow_flex": [float(np.min(elbow)), float(np.max(elbow))],
            },
            "scientific_claims_allowed": False,
            "source": "analytic sine waves, not human measurements",
        }
        report_path = resolve(config["target_report"])
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Generation synthetique impossible: {exc}", file=sys.stderr)
        return 2
    print(f"Cible synthetique: {target_path}")
    print(f"Rapport: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
