"""Compare motion-quality reports without changing their scientific thresholds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def load(path: str) -> dict:
    return json.loads(resolve(path).read_text(encoding="utf-8"))


def summarize(report: dict) -> dict:
    missing = {name: values["missing_rate"] for name, values in report["markers"].items()}
    segment_cv = {name: values["cv"] for name, values in report["segments"].items()}
    return {
        "status": report["status"],
        "rows": report["rows"],
        "fps": report["inferred_fps"],
        "maximum_marker_missing_rate": max(missing.values()),
        "marker_missing_rate": missing,
        "maximum_segment_cv": max(segment_cv.values()),
        "segment_cv": segment_cv,
        "failures": report["failures"],
    }


def preferred(first_name: str, first: dict, second_name: str, second: dict) -> dict:
    first_key = (first["maximum_marker_missing_rate"], first["maximum_segment_cv"])
    second_key = (second["maximum_marker_missing_rate"], second["maximum_segment_cv"])
    winner = first_name if first_key < second_key else second_name
    return {
        "preferred": winner,
        "rule": "lowest maximum missing rate, then lowest maximum segment CV",
        "both_pass": first["status"] == second["status"] == "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video1-right", default="data/scenarios/scenarios_secondaires/video_principale_methode_v1/motion_quality.json")
    parser.add_argument("--test1-right", default="data/scenarios/scenarios_secondaires/video_secondaire_methode_v1/motion_quality.json")
    parser.add_argument("--video1-left", default="data/scenarios/scenarios_secondaires/video_principale_methode_v1/motion_quality_left.json")
    parser.add_argument("--test1-left", default="data/scenarios/scenarios_secondaires/video_secondaire_methode_v1/motion_quality_left.json")
    parser.add_argument("--output", default="data/scenarios/scenarios_secondaires/comparaison_video_principale_vs_secondaire_methode_v1/comparison.json")
    args = parser.parse_args()

    reports = {
        "video1_right": summarize(load(args.video1_right)),
        "test1_right": summarize(load(args.test1_right)),
        "video1_left": summarize(load(args.video1_left)),
        "test1_left": summarize(load(args.test1_left)),
    }
    comparison = {
        "schema_version": 1,
        "reports": reports,
        "right_arm": preferred("video1", reports["video1_right"], "test1", reports["test1_right"]),
        "left_arm": preferred("video1", reports["video1_left"], "test1", reports["test1_left"]),
        "scientific_decision": "NEITHER_VIDEO_PASSES_MOTION_QUALITY",
    }
    output = resolve(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(comparison, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Comparaison: {output}")
    print("Bras droit prefere:", comparison["right_arm"]["preferred"])
    print("Bras gauche prefere:", comparison["left_arm"]["preferred"])
    print("Decision:", comparison["scientific_decision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
