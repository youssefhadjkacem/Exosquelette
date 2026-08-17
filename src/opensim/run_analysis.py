"""Run a gated OpenSim IK/ID/SO analysis and save reproducible setup files."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SRC_ROOT.parent
sys.path.insert(0, str(SRC_ROOT))

from pipeline_utils import dump_json, resolve_project_path  # noqa: E402


def configure_opensim_dlls(home: Path) -> None:
    if not hasattr(os, "add_dll_directory"):
        return
    for candidate in (home / "bin", home / "sdk" / "lib", home / "sdk" / "Python" / "opensim"):
        if candidate.exists():
            os.add_dll_directory(str(candidate))


def require_quality_gate(path: Path, allow_failed: bool) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        report = json.load(stream)
    if report.get("status") != "PASS" and not allow_failed:
        failures = "\n".join(f"- {item}" for item in report.get("failures", []))
        raise RuntimeError(f"Qualite mouvement insuffisante:\n{failures}")
    return report


def build_ik_tool(opensim, model, trc: Path, output: Path, results_dir: Path):
    marker_data = opensim.MarkerData(str(trc))
    tool = opensim.InverseKinematicsTool()
    tool.setName("ironing_inverse_kinematics")
    tool.setModel(model)
    tool.setMarkerDataFileName(str(trc))
    tool.setOutputMotionFileName(str(output))
    tool.setResultsDir(str(results_dir))
    tool.setStartTime(marker_data.getStartFrameTime())
    tool.setEndTime(marker_data.getLastFrameTime())
    tool.set_report_errors(True)
    tool.set_report_marker_locations(True)
    tasks = opensim.IKTaskSet()
    marker_set = model.getMarkerSet()
    for index in range(marker_set.getSize()):
        task = opensim.IKMarkerTask()
        task.setName(marker_set.get(index).getName())
        task.setApply(True)
        task.setWeight(1.0)
        tasks.cloneAndAppend(task)
    tool.set_IKTaskSet(tasks)
    return tool, marker_data.getStartFrameTime(), marker_data.getLastFrameTime()


def build_id_tool(opensim, model, coordinates: Path, external_loads: Path, output: Path, results_dir: Path, start: float, end: float, cutoff: float):
    tool = opensim.InverseDynamicsTool()
    tool.setName("ironing_inverse_dynamics")
    tool.setModel(model)
    tool.setCoordinatesFileName(str(coordinates))
    tool.setExternalLoadsFileName(str(external_loads))
    tool.setOutputGenForceFileName(output.name)
    tool.setResultsDir(str(results_dir))
    tool.setStartTime(start)
    tool.setEndTime(end)
    tool.setLowpassCutoffFrequency(cutoff)
    return tool


def build_so_tool(opensim, model, coordinates: Path, external_loads: Path, results_dir: Path, start: float, end: float, cutoff: float):
    tool = opensim.AnalyzeTool()
    tool.setName("ironing_static_optimization")
    tool.setModel(model)
    tool.setCoordinatesFileName(str(coordinates))
    tool.setExternalLoadsFileName(str(external_loads))
    tool.setResultsDir(str(results_dir))
    tool.setInitialTime(start)
    tool.setFinalTime(end)
    tool.setLowpassCutoffFrequency(cutoff)
    analysis = opensim.StaticOptimization()
    analysis.setName("StaticOptimization")
    analysis.setStartTime(start)
    analysis.setEndTime(end)
    analysis.setUseModelForceSet(True)
    analysis.setUseMusclePhysiology(True)
    tool.updAnalysisSet().cloneAndAppend(analysis)
    return tool


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="data/opensim/arm26_scaled.osim")
    parser.add_argument("--trc", default="data/motion_data.trc")
    parser.add_argument("--quality-report", default="data/results/motion_quality.json")
    parser.add_argument("--results-dir", default="data/results/opensim")
    parser.add_argument("--opensim-home", default=os.environ.get("OPENSIM_HOME", r"C:\OpenSim 4.5"))
    parser.add_argument("--external-loads", help="XML OpenSim des forces fer/table; requis pour --id ou --so.")
    parser.add_argument("--id", action="store_true")
    parser.add_argument("--so", action="store_true")
    parser.add_argument("--cutoff-hz", type=float, default=6.0)
    parser.add_argument("--allow-failed-quality", action="store_true", help="Exploration uniquement.")
    args = parser.parse_args(argv)

    model_path, trc_path = resolve_project_path(args.model), resolve_project_path(args.trc)
    quality_path = resolve_project_path(args.quality_report)
    results_dir = resolve_project_path(args.results_dir)
    if (args.id or args.so) and not args.external_loads:
        print("--external-loads est obligatoire pour ID/SO dans le cas du repassage.", file=sys.stderr)
        return 2
    results_dir.mkdir(parents=True, exist_ok=True)
    try:
        quality = require_quality_gate(quality_path, args.allow_failed_quality)
        configure_opensim_dlls(Path(args.opensim_home))
        import opensim
        try:
            opensim.Logger.removeFileSink()
        except Exception:
            pass
        opensim.Logger.addFileSink(str(results_dir / "opensim.log"))
        model = opensim.Model(str(model_path))
        model.initSystem()
    except (OSError, ImportError, RuntimeError, ValueError) as exc:
        print(f"Initialisation OpenSim impossible: {exc}", file=sys.stderr)
        return 1

    ik_output = results_dir / "ik_results.mot"
    try:
        ik_tool, start, end = build_ik_tool(opensim, model, trc_path, ik_output, results_dir)
        ik_tool.printToXML(str(results_dir / "ik_setup.xml"))
        if not ik_tool.run():
            raise RuntimeError("Inverse Kinematics a retourne false")

        external_loads = resolve_project_path(args.external_loads) if args.external_loads else None
        if args.id:
            id_output = results_dir / "id_results.sto"
            id_tool = build_id_tool(opensim, model, ik_output, external_loads, id_output, results_dir, start, end, args.cutoff_hz)
            id_tool.printToXML(str(results_dir / "id_setup.xml"))
            if not id_tool.run():
                raise RuntimeError("Inverse Dynamics a retourne false")
        if args.so:
            so_tool = build_so_tool(opensim, model, ik_output, external_loads, results_dir, start, end, args.cutoff_hz)
            so_tool.printToXML(str(results_dir / "so_setup.xml"))
            if not so_tool.run():
                raise RuntimeError("Static Optimization a retourne false")
    except Exception as exc:  # OpenSim raises wrapped C++ exceptions.
        print(f"Analyse OpenSim echouee: {exc}", file=sys.stderr)
        return 1

    metadata = {
        "schema_version": 1,
        "model": str(model_path), "trc": str(trc_path),
        "quality_report": str(quality_path), "quality_status": quality.get("status"),
        "time_range_s": [start, end], "cutoff_hz": args.cutoff_hz,
        "inverse_kinematics": True, "inverse_dynamics": args.id,
        "static_optimization": args.so,
        "external_loads": str(external_loads) if external_loads else None,
        "exploratory_override": args.allow_failed_quality,
    }
    dump_json(results_dir / "analysis_metadata.json", metadata)
    print(f"Analyse terminee: {results_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
