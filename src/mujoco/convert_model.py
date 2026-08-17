"""Convert an OpenSim model with MyoConverter using portable Windows paths."""

from __future__ import annotations

import argparse
import multiprocessing
import os
import sys
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_ROOT))
from pipeline_utils import resolve_project_path  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output-dir", default="models/mujoco/converted")
    parser.add_argument("--opensim-home", default=os.environ.get("OPENSIM_HOME", r"C:\OpenSim 4.5"))
    parser.add_argument("--geometry", default=None)
    args = parser.parse_args(argv)
    home = Path(args.opensim_home)
    if hasattr(os, "add_dll_directory"):
        for path in (home / "bin", home / "sdk" / "lib", home / "sdk" / "Python" / "opensim"):
            if path.exists():
                os.add_dll_directory(str(path))
    model = resolve_project_path(args.model)
    geometry = Path(args.geometry) if args.geometry else home / "Geometry"
    output = resolve_project_path(args.output_dir)
    if not model.exists() or not geometry.exists():
        print(f"Modele ou geometrie absent: {model}, {geometry}", file=sys.stderr)
        return 2
    output.mkdir(parents=True, exist_ok=True)
    try:
        from myoconverter.O2MPipeline import O2MPipeline
        O2MPipeline(str(model), str(geometry), str(output))
    except Exception as exc:
        print(f"Conversion echouee: {exc}", file=sys.stderr)
        return 1
    print(f"Conversion MyoConverter: {output}")
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
