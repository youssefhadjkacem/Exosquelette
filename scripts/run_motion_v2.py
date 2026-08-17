"""Run the constrained monocular V2 pipeline and create an exploratory TRC."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def run(command: list[str], allowed_returncodes: tuple[int, ...] = (0,)) -> None:
    print(" ".join(command))
    completed = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    if completed.returncode not in allowed_returncodes:
        raise RuntimeError(f"Commande echouee avec le code {completed.returncode}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/scenarios/video1_v2.json")
    parser.add_argument(
        "--report-on-fail", action="store_true",
        help=(
            "Conserver le rapport d'un scenario qui echoue et retourner succes sans "
            "generer les cibles TRC/MOT. Utile pour une comparaison de robustesse."
        ),
    )
    args = parser.parse_args(argv)
    try:
        config_path = resolve(args.config)
        config = json.loads(config_path.read_text(encoding="utf-8"))
        run([
            sys.executable, str(PROJECT_ROOT / "src" / "reconstruct_planar_arm.py"),
            "--config", str(config_path),
        ], allowed_returncodes=(0, 1) if args.report_on_fail else (0,))
        report = json.loads(resolve(config["output_report"]).read_text(encoding="utf-8"))
        if report.get("status") != "EXPLORATORY_PASS":
            if args.report_on_fail:
                print("Scenario conserve pour comparaison malgre l'echec des controles.")
                print("TRC et cible MuJoCo non generes pour ce scenario.")
                return 0
            raise RuntimeError("La reconstruction V2 n'a pas passe ses controles exploratoires.")
        run([
            sys.executable, str(PROJECT_ROOT / "src" / "convert_to_trc.py"),
            "--input", str(resolve(config["output_motion"])),
            "--output", str(resolve(config["output_trc"])),
            "--calibration", str(resolve(config["calibration"])),
            "--side", "right", "--allow-unvalidated-calibration",
        ])
        run([
            sys.executable, str(PROJECT_ROOT / "src" / "create_mujoco_target.py"),
            "--config", str(config_path),
        ])
    except (OSError, KeyError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"Pipeline V2 interrompu: {exc}", file=sys.stderr)
        return 1
    print("Pipeline V2 termine en mode EXPLORATOIRE.")
    print("Le TRC et la cible MOT produits ne debloquent pas OpenSim quantitatif.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
