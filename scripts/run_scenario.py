"""Execute the reproducible motion stages of a configured scenario."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def run_stage(name: str, command: list[str]) -> dict:
    print(f"\n=== {name} ===")
    print(" ".join(command))
    completed = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Etape '{name}' echouee (code {completed.returncode}).")
    return {"name": name, "status": "COMPLETED", "command": command}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", default="config/scenarios/video1_v1.json",
        help="Configuration JSON relative a la racine du projet.",
    )
    parser.add_argument(
        "--skip-extraction", action="store_true",
        help="Reutiliser le CSV brut existant.",
    )
    parser.add_argument(
        "--report-on-fail", action="store_true",
        help="Conserver un scenario en echec comme evidence comparative sans retourner une erreur.",
    )
    args = parser.parse_args(argv)

    config_path = project_path(args.config)
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        acquisition = config["acquisition"]
        processing = config["processing"]
        gates = config["quality_gates"]
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"Configuration invalide: {exc}", file=sys.stderr)
        return 2

    raw_csv = project_path(processing["raw_csv"])
    smoothed_csv = project_path(processing["smoothed_csv"])
    motion_report_path = project_path(processing["motion_report"])
    scenario_report_path = project_path(processing["scenario_report"])
    scenario_report_path.parent.mkdir(parents=True, exist_ok=True)
    stages: list[dict] = []

    try:
        if args.skip_extraction:
            if not raw_csv.exists():
                raise RuntimeError(f"CSV brut absent: {raw_csv}")
            stages.append({"name": "extraction", "status": "REUSED", "artifact": str(raw_csv)})
        else:
            stages.append(run_stage("extraction", [
                sys.executable, str(PROJECT_ROOT / "src" / "extract_motion.py"),
                "--video", str(project_path(acquisition["video"])),
                "--output", str(raw_csv),
            ]))

        stages.append(run_stage("smoothing", [
            sys.executable, str(PROJECT_ROOT / "src" / "smooth_motion.py"),
            "--input", str(raw_csv), "--output", str(smoothed_csv),
            "--cutoff-hz", str(processing["cutoff_hz"]),
            "--order", str(processing["filter_order"]),
            "--max-gap-frames", str(processing["max_interpolation_gap_frames"]),
            "--min-visibility", str(processing["minimum_visibility"]),
        ]))
        stages.append(run_stage("motion_quality", [
            sys.executable, str(PROJECT_ROOT / "src" / "validate_motion.py"),
            "--input", str(smoothed_csv), "--output", str(motion_report_path),
            "--required-markers", ",".join(processing["required_markers"]),
            "--max-missing-rate", str(gates["max_missing_rate"]),
            "--max-segment-cv", str(gates["max_segment_cv"]),
            "--max-frame-gap", str(gates["max_frame_gap"]),
            "--report-only",
        ]))
        motion_report = json.loads(motion_report_path.read_text(encoding="utf-8"))
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    passed = motion_report.get("status") == "PASS"
    report = {
        "schema_version": 1,
        "scenario_id": config.get("scenario_id"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.executable,
        "configuration": str(config_path),
        "stages": stages,
        "motion_quality": motion_report,
        "decision": {
            "status": "READY_FOR_CALIBRATION_AND_TRC" if passed else "BLOCKED_AT_MOTION_QUALITY",
            "opensim_allowed": passed,
            "rl_allowed": False,
            "reason": (
                "Le mouvement passe les seuils; une calibration metrique valide reste obligatoire."
                if passed else
                "Le mouvement ne passe pas les seuils. OpenSim quantitatif et RL restent bloques."
            ),
        },
    }
    scenario_report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nRapport du scenario: {scenario_report_path}")
    print(f"Decision: {report['decision']['status']}")
    return 0 if passed or args.report_on_fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
