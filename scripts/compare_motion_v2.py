"""Compare two constrained V2 motion scenarios and build an auditable report."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy.signal import find_peaks  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANGLE_FIELDS = ("shoulder_planar_angle_deg", "elbow_interior_angle_deg")


def resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_json(path: str) -> dict:
    return json.loads(resolve(path).read_text(encoding="utf-8"))


def load_motion(path: str) -> list[dict[str, str]]:
    with resolve(path).open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def number(value: str | float | int | None) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return math.nan
    return result if math.isfinite(result) else math.nan


def longest_finite_run(values: np.ndarray) -> tuple[int, int]:
    best_start = best_end = start = 0
    in_run = False
    for index, finite in enumerate(np.isfinite(values)):
        if finite and not in_run:
            start, in_run = index, True
        if in_run and (not finite or index == len(values) - 1):
            end = index if finite else index - 1
            if end - start > best_end - best_start:
                best_start, best_end = start, end
            in_run = False
    return best_start, best_end


def estimate_cycles(rows: list[dict[str, str]], fps: float, coverage: float) -> dict:
    values = np.asarray([number(row.get("shoulder_planar_angle_deg")) for row in rows])
    if coverage < 0.8:
        return {
            "status": "NOT_ESTIMATED",
            "count": None,
            "reason": "valid coverage below 80%",
        }
    start, end = longest_finite_run(values)
    segment = values[start:end + 1]
    if len(segment) < max(20, round(2 * fps)):
        return {
            "status": "NOT_ESTIMATED",
            "count": None,
            "reason": "no continuous valid segment of at least 2 seconds",
        }
    prominence = max(5.0, float(np.ptp(segment)) * 0.15)
    peaks, _ = find_peaks(segment, prominence=prominence, distance=max(1, round(0.5 * fps)))
    return {
        "status": "EXPLORATORY_ESTIMATE",
        "count": max(0, int(len(peaks) - 1)),
        "peak_count": int(len(peaks)),
        "prominence_deg": prominence,
        "continuous_frames": int(len(segment)),
        "reason": "peak-to-peak shoulder oscillations in the longest valid segment",
    }


def summarize(name: str, report: dict, rows: list[dict[str, str]]) -> dict:
    total = int(report["total_rows"])
    valid = int(report["valid_rows"])
    reliable = int(report["raw_reliable_direction_rows"])
    times = np.asarray([number(row.get("time_s")) for row in rows])
    finite_times = times[np.isfinite(times)]
    duration = float(np.ptp(finite_times)) if len(finite_times) else 0.0
    fps = (len(finite_times) - 1) / duration if duration > 0 else math.nan
    statistics = report["kinematic_quality"]["statistics"]
    coverage = valid / total if total else 0.0
    return {
        "scenario": name,
        "status": report["status"],
        "total_rows": total,
        "valid_rows": valid,
        "valid_coverage": coverage,
        "raw_reliable_rows": reliable,
        "raw_reliable_coverage": reliable / total if total else 0.0,
        "duration_s": duration,
        "fps": fps,
        "shoulder_range_deg": statistics["shoulder_planar"]["range_deg"],
        "elbow_range_deg": statistics["elbow_flexion"]["range_deg"],
        "shoulder_p95_velocity_deg_s": statistics["shoulder_planar"]["p95_abs_velocity_deg_s"],
        "elbow_p95_velocity_deg_s": statistics["elbow_flexion"]["p95_abs_velocity_deg_s"],
        "shoulder_p95_acceleration_deg_s2": statistics["shoulder_planar"]["p95_abs_acceleration_deg_s2"],
        "elbow_p95_acceleration_deg_s2": statistics["elbow_flexion"]["p95_abs_acceleration_deg_s2"],
        "cycles": estimate_cycles(rows, fps, coverage),
    }


def trajectory_rows(name: str, rows: list[dict[str, str]]) -> list[dict[str, object]]:
    if not rows:
        return []
    denominator = max(1, len(rows) - 1)
    output = []
    for index, row in enumerate(rows):
        output.append({
            "scenario": name,
            "frame": int(number(row.get("frame"))),
            "time_s": number(row.get("time_s")),
            "progress_pct": 100.0 * index / denominator,
            "source_valid": int(number(row.get("source_valid")) or 0),
            "shoulder_angle_deg": number(row.get(ANGLE_FIELDS[0])),
            "elbow_angle_deg": number(row.get(ANGLE_FIELDS[1])),
        })
    return output


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def render_figure(path: Path, summaries: list[dict], trajectories: list[dict]) -> None:
    palette = {"video1": "#2463A7", "test1": "#D68127"}
    fig, axes = plt.subplots(3, 1, figsize=(11, 11), constrained_layout=True)
    names = [item["scenario"] for item in summaries]
    coverage = [100.0 * item["valid_coverage"] for item in summaries]
    bars = axes[0].bar(names, coverage, color=[palette[name] for name in names], edgecolor="#263238")
    axes[0].axhline(98.0, color="#555555", linestyle="--", linewidth=1.2, label="Seuil minimal 98 %")
    axes[0].set_ylim(0, 105)
    axes[0].set_ylabel("Frames valides (%)")
    axes[0].set_title("Couverture valide du bras droit")
    axes[0].legend(frameon=False, loc="upper right")
    axes[0].bar_label(bars, fmt="%.1f %%", padding=3)

    for scenario in names:
        selected = [row for row in trajectories if row["scenario"] == scenario]
        progress = [row["progress_pct"] for row in selected]
        axes[1].plot(progress, [row["shoulder_angle_deg"] for row in selected],
                     label=scenario, color=palette[scenario], linewidth=1.5)
        axes[2].plot(progress, [row["elbow_angle_deg"] for row in selected],
                     label=scenario, color=palette[scenario], linewidth=1.5)
    for axis, title in zip(axes[1:], ("Angle planaire de l'épaule", "Angle intérieur du coude")):
        axis.set_xlim(0, 100)
        axis.set_xlabel("Progression dans la fenêtre analysée (%)")
        axis.set_ylabel("Angle (degrés)")
        axis.set_title(title)
        axis.grid(axis="y", color="#D9DEE3", linewidth=0.7)
        axis.legend(frameon=False, ncol=2)
    fig.suptitle("Comparaison exploratoire video1 / test1 — bras droit", fontsize=15)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, facecolor="white")
    plt.close(fig)


def format_optional_cycle(summary: dict) -> str:
    cycles = summary["cycles"]
    return str(cycles["count"]) if cycles["count"] is not None else "non estimé"


def build_markdown(comparison: dict, figure_name: str) -> str:
    first, second = comparison["scenarios"]
    return f"""# Comparaison V2 de `video1` et `test1`

## Résumé technique

`video1` reste la référence exploratoire actuelle. Sa couverture valide atteint **{first['valid_coverage']:.1%}**, contre **{second['valid_coverage']:.1%}** pour `test1`. Le second enregistrement échoue donc au contrôle géométrique et ne doit pas alimenter OpenSim, le contrôleur d'assistance ou le RL.

La comparaison établit surtout un effet de prise de vue : les données actuelles ne permettent pas d'attribuer les différences d'angle au geste réel plutôt qu'aux occultations et à l'orientation de la caméra.

## Résultats et visualisation

![Couverture et trajectoires angulaires]({figure_name})

Les interruptions visibles dans les courbes de `test1` correspondent aux frames pour lesquelles la direction complète épaule–coude–poignet n'est pas fiable. Les courbes ne sont pas interpolées à travers ces longues absences.

| Indicateur | `video1` | `test1` |
|---|---:|---:|
| Statut V2 | {first['status']} | {second['status']} |
| Frames analysées | {first['total_rows']} | {second['total_rows']} |
| Frames valides | {first['valid_rows']} ({first['valid_coverage']:.1%}) | {second['valid_rows']} ({second['valid_coverage']:.1%}) |
| Durée de la fenêtre | {first['duration_s']:.2f} s | {second['duration_s']:.2f} s |
| Amplitude épaule | {first['shoulder_range_deg']:.1f}° | {second['shoulder_range_deg']:.1f}°* |
| Amplitude coude | {first['elbow_range_deg']:.1f}° | {second['elbow_range_deg']:.1f}°* |
| Cycles exploratoires | {format_optional_cycle(first)} | {format_optional_cycle(second)} |

\* Les amplitudes de `test1` ne décrivent que 154 frames valides discontinues et ne sont pas directement comparables à celles de `video1`.

## Périmètre, définitions et méthode

- Population : bras droit anatomique tenant le fer, confirmé visuellement dans les deux vidéos.
- Fenêtres : frames 0–1080 pour `video1` et 0–803 pour `test1`.
- Reconstruction : plan caméra, longueurs fixes de 0,30 m et 0,25 m, filtre Butterworth 2 Hz.
- Couverture valide : frames possédant simultanément une direction exploitable du bras et de l'avant-bras après interpolation limitée à 10 frames.
- Seuil : au plus 2 % de données manquantes, soit au moins 98 % de couverture.
- Cycles : oscillations pic-à-pic de l'angle d'épaule sur le plus long segment continu ; aucune estimation sous 80 % de couverture.

## Limites et contrôle de robustesse

- Une seule caméra ne mesure pas la profondeur.
- Les longueurs segmentaires et l'anthropométrie sont supposées, non mesurées sur le sujet.
- Les deux vidéos n'ont ni la même durée, ni la même fréquence, ni le même point de vue.
- Le statut cinématique local de `test1` ne compense pas son échec de couverture : les vitesses calculées sur les rares fragments visibles ne valident pas la vidéo complète.
- Cette analyse est descriptive et exploratoire ; elle ne prouve pas une différence biomécanique entre deux gestes.

## Décision et prochaine acquisition

1. Conserver `video1` comme référence de développement.
2. Ne pas générer de cible MuJoCo/OpenSim depuis `test1`.
3. Refilmer le bras droit avec épaule, coude, poignet et fer visibles pendant tout le cycle.
4. Utiliser deux caméras synchronisées, idéalement une vue latérale et une vue oblique, avec une référence métrique visible.
5. Rejouer ce rapport et exiger deux scénarios en `EXPLORATORY_PASS` avant toute comparaison d'assistance ou préparation RL.

## Questions encore ouvertes

- Combien de cycles complets faut-il conserver pour représenter une tâche industrielle répétitive ?
- Quelle masse réelle du fer et quelles forces de contact avec la table doivent être intégrées ?
- La prochaine acquisition permettra-t-elle une reconstruction 3D calibrée plutôt qu'une approximation planaire ?
"""


def build_portable_artifact(comparison: dict, trajectories: list[dict]) -> dict:
    """Build the canonical report payload used by the portable analytics reader."""
    generated_at = datetime.now(timezone.utc).isoformat()
    summary_rows = []
    for item in comparison["scenarios"]:
        summary_rows.append({
            "scenario": item["scenario"],
            "status": item["status"],
            "valid_coverage": item["valid_coverage"],
            "valid_rows": item["valid_rows"],
            "total_rows": item["total_rows"],
            "duration_s": item["duration_s"],
            "shoulder_range_deg": item["shoulder_range_deg"],
            "elbow_range_deg": item["elbow_range_deg"],
            "cycle_count": item["cycles"]["count"],
        })
    portable_trajectories = [
        {
            key: (None if isinstance(value, float) and not math.isfinite(value) else value)
            for key, value in row.items()
        }
        for row in trajectories
    ]
    summary_sql = (
        "SELECT scenario, status, valid_coverage, valid_rows, total_rows, duration_s, "
        "shoulder_range_deg, elbow_range_deg, cycle_count FROM summary ORDER BY scenario"
    )
    trajectory_sql = (
        "SELECT scenario, frame, time_s, progress_pct, source_valid, shoulder_angle_deg, "
        "elbow_angle_deg FROM trajectories ORDER BY scenario, frame"
    )

    def execute_snapshot_query(table: str, rows: list[dict], sql: str) -> list[dict]:
        columns = list(rows[0])
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        try:
            definitions = []
            for column in columns:
                numeric = all(
                    value is None or isinstance(value, (int, float, bool))
                    for value in (row[column] for row in rows)
                )
                definitions.append(f'"{column}" {"REAL" if numeric else "TEXT"}')
            connection.execute(f'CREATE TABLE "{table}" ({", ".join(definitions)})')
            placeholders = ", ".join("?" for _ in columns)
            connection.executemany(
                f'INSERT INTO "{table}" VALUES ({placeholders})',
                ([row[column] for column in columns] for row in rows),
            )
            return [dict(row) for row in connection.execute(sql).fetchall()]
        finally:
            connection.close()

    summary_rows = execute_snapshot_query("summary", summary_rows, summary_sql)
    portable_trajectories = execute_snapshot_query(
        "trajectories", portable_trajectories, trajectory_sql
    )
    sources = [
        {
            "id": "comparison",
            "label": "Comparaison V2 calculée",
            "path": "data/scenarios/scenarios_secondaires/comparaison_video_principale_vs_secondaire/comparison.json",
            "query": {
                "engine": "sqlite",
                "sql": summary_sql,
                "description": "Lecture de la synthèse calculée par compare_motion_v2.py",
                "language": "sql",
                "tables_used": ["summary"],
                "filters": ["right anatomical arm", "full configured activity windows"],
                "metric_definitions": [
                    "valid_coverage = valid_rows / total_rows",
                    "cycle_count is omitted below 80 percent valid coverage",
                ],
            },
        },
        {
            "id": "trajectories",
            "label": "Trajectoires angulaires V2",
            "path": "data/scenarios/scenarios_secondaires/comparaison_video_principale_vs_secondaire/comparison_trajectories.csv",
            "query": {
                "engine": "sqlite",
                "sql": trajectory_sql,
                "description": "Lecture ordonnée des trajectoires produites par compare_motion_v2.py",
                "language": "sql",
                "tables_used": ["trajectories"],
                "filters": ["right anatomical arm", "2 Hz angle filter", "maximum gap 10 frames"],
            },
        },
    ]
    manifest = {
        "version": 1,
        "surface": "report",
        "title": "Comparaison V2 de video1 et test1",
        "description": "Robustesse de la reconstruction monoculaire du bras droit pendant le repassage.",
        "generatedAt": generated_at,
        "sources": sources,
        "cards": [
            {
                "id": "video1_coverage",
                "description": "Couverture valide de video1",
                "dataset": "summary",
                "filter": {"scenario": "video1"},
                "sourceId": "comparison",
                "metrics": [{"label": "Video1 — frames valides", "field": "valid_coverage", "format": "percent"}],
            },
            {
                "id": "test1_coverage",
                "description": "Couverture valide de test1",
                "dataset": "summary",
                "filter": {"scenario": "test1"},
                "sourceId": "comparison",
                "metrics": [{"label": "Test1 — frames valides", "field": "valid_coverage", "format": "percent"}],
            },
        ],
        "charts": [
            {
                "id": "coverage_chart",
                "title": "Couverture valide du bras droit",
                "subtitle": "Part des frames reconstruites; seuil minimal attendu : 98 %",
                "showDescription": True,
                "type": "bar",
                "dataset": "summary",
                "sourceId": "comparison",
                "encodings": {
                    "x": {"field": "scenario", "type": "nominal", "label": "Vidéo"},
                    "y": {"field": "valid_coverage", "type": "quantitative", "format": "percent", "label": "Frames valides"},
                },
                "layout": "full",
            },
            {
                "id": "shoulder_chart",
                "title": "Angle planaire de l'épaule",
                "subtitle": "Fenêtres complètes normalisées de 0 à 100 %; les lacunes de test1 restent visibles",
                "showDescription": True,
                "type": "line",
                "dataset": "trajectories",
                "sourceId": "trajectories",
                "encodings": {
                    "x": {"field": "progress_pct", "type": "quantitative", "label": "Progression", "unit": "%"},
                    "y": {"field": "shoulder_angle_deg", "type": "quantitative", "label": "Angle", "unit": "°"},
                    "color": {"field": "scenario", "type": "nominal", "label": "Vidéo"},
                },
                "layout": "full",
            },
            {
                "id": "elbow_chart",
                "title": "Angle intérieur du coude",
                "subtitle": "Fenêtres complètes normalisées de 0 à 100 %; comparaison descriptive uniquement",
                "showDescription": True,
                "type": "line",
                "dataset": "trajectories",
                "sourceId": "trajectories",
                "encodings": {
                    "x": {"field": "progress_pct", "type": "quantitative", "label": "Progression", "unit": "%"},
                    "y": {"field": "elbow_angle_deg", "type": "quantitative", "label": "Angle", "unit": "°"},
                    "color": {"field": "scenario", "type": "nominal", "label": "Vidéo"},
                },
                "layout": "full",
            },
        ],
        "tables": [
            {
                "id": "summary_table",
                "title": "Indicateurs des deux scénarios",
                "subtitle": "Même bras, même reconstruction et mêmes seuils; fenêtres configurées complètes",
                "showDescription": True,
                "dataset": "summary",
                "defaultSort": {"field": "valid_coverage", "direction": "desc"},
                "density": "spacious",
                "sourceId": "comparison",
                "layout": "full",
                "columns": [
                    {"field": "scenario", "label": "Scénario", "type": "text"},
                    {"field": "status", "label": "Statut", "type": "text"},
                    {"field": "valid_coverage", "label": "Couverture", "format": "percent"},
                    {"field": "valid_rows", "label": "Frames valides", "format": "number"},
                    {"field": "total_rows", "label": "Frames totales", "format": "number"},
                    {"field": "duration_s", "label": "Durée (s)", "format": "number"},
                    {"field": "shoulder_range_deg", "label": "Amplitude épaule (°)", "format": "number"},
                    {"field": "elbow_range_deg", "label": "Amplitude coude (°)", "format": "number"},
                ],
            }
        ],
        "blocks": [
            {"id": "title", "type": "markdown", "body": "# Comparaison V2 de video1 et test1", "layout": "full"},
            {
                "id": "technical_summary", "type": "markdown", "layout": "full", "sourceId": "comparison",
                "body": "## Test1 ne permet pas une comparaison biomécanique fiable\n\n**Video1 reste la référence exploratoire.** Sa couverture est de 100 %, contre 19,2 % pour test1. Les différences angulaires peuvent provenir de la caméra et des occultations; test1 reste bloquée pour OpenSim, MuJoCo et le RL.",
            },
            {"id": "metric_strip", "type": "metric-strip", "cardIds": ["video1_coverage", "test1_coverage"], "layout": "full"},
            {
                "id": "coverage_finding", "type": "markdown", "layout": "full", "sourceId": "comparison",
                "body": "## L'occultation du bras droit explique l'échec de test1\n\nLa couverture est calculée sur toutes les frames configurées. Le seuil de 98 % est dépassé par video1 et manqué de 78,8 points par test1. Une courte fenêtre favorable n'a pas été sélectionnée afin de ne pas masquer le problème de prise de vue.",
            },
            {"id": "coverage_visual", "type": "chart", "chartId": "coverage_chart", "layout": "full"},
            {
                "id": "trajectory_finding", "type": "markdown", "layout": "full", "sourceId": "trajectories",
                "body": "## Les trajectoires de test1 sont trop fragmentées pour conclure\n\nLes segments orange sont les seules périodes fiables de test1. Les absences longues ne sont pas interpolées. Les amplitudes calculées sur ces fragments ne décrivent donc pas la vidéo complète et ne doivent pas être comparées quantitativement à video1.",
            },
            {"id": "shoulder_visual", "type": "chart", "chartId": "shoulder_chart", "layout": "full"},
            {"id": "elbow_visual", "type": "chart", "chartId": "elbow_chart", "layout": "full"},
            {
                "id": "scope_methods", "type": "markdown", "layout": "full",
                "body": "## Mesures identiques appliquées aux deux vidéos\n\nLe bras étudié est le bras droit anatomique tenant le fer. La reconstruction impose des segments de 0,30 m et 0,25 m dans le plan caméra, filtre les angles à 2 Hz et n'interpole que les lacunes d'au plus 10 frames. La couverture valide exige une direction complète épaule–coude–poignet.",
            },
            {"id": "summary_table_block", "type": "table", "tableId": "summary_table", "layout": "full"},
            {
                "id": "limitations", "type": "markdown", "layout": "full",
                "body": "## Une nouvelle acquisition est nécessaire avant OpenSim ou RL\n\nCette analyse monoculaire ne mesure pas la profondeur et utilise une anthropométrie supposée. Les durées, fréquences et points de vue diffèrent. Refilmer avec deux caméras synchronisées, une référence métrique et le bras droit entièrement visible; exiger ensuite deux scénarios en EXPLORATORY_PASS.",
            },
            {
                "id": "questions", "type": "markdown", "layout": "full",
                "body": "## Questions pour la prochaine campagne\n\n- Combien de cycles complets représentent la tâche industrielle ?\n- Quelle masse du fer et quelles forces de contact faut-il mesurer ?\n- La prochaine acquisition permettra-t-elle une reconstruction 3D calibrée ?",
            },
        ],
    }
    return {
        "surface": "report",
        "manifest": manifest,
        "snapshot": {
            "version": 1,
            "generatedAt": generated_at,
            "status": "ready",
            "datasets": {"summary": summary_rows, "trajectories": portable_trajectories},
        },
        "sources": sources,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video1-report", default="data/scenarios/scenario_principal/motion_quality_v2.json")
    parser.add_argument("--video1-motion", default="data/scenarios/scenario_principal/motion_constrained.csv")
    parser.add_argument("--test1-report", default="data/scenarios/scenarios_secondaires/video_secondaire_methode_v2/motion_quality_v2.json")
    parser.add_argument("--test1-motion", default="data/scenarios/scenarios_secondaires/video_secondaire_methode_v2/motion_constrained.csv")
    parser.add_argument("--output-dir", default="data/scenarios/scenarios_secondaires/comparaison_video_principale_vs_secondaire")
    args = parser.parse_args(argv)

    output_dir = resolve(args.output_dir)
    source_pairs = [
        ("video1", args.video1_report, args.video1_motion),
        ("test1", args.test1_report, args.test1_motion),
    ]
    summaries, trajectories = [], []
    for name, report_path, motion_path in source_pairs:
        rows = load_motion(motion_path)
        summaries.append(summarize(name, load_json(report_path), rows))
        trajectories.extend(trajectory_rows(name, rows))

    comparable = all(item["status"] == "EXPLORATORY_PASS" for item in summaries)
    comparison = {
        "schema_version": 2,
        "status": "COMPARABLE_EXPLORATORY" if comparable else "NOT_COMPARABLE",
        "task_arm": "right",
        "scenarios": summaries,
        "decision": {
            "preferred_reference": "video1",
            "camera_robustness_pass": comparable,
            "opensim_allowed": False,
            "rl_allowed": False,
            "reason": (
                "Both scenarios passed the same exploratory gates."
                if comparable else
                "test1 does not pass right-arm coverage; observed angle differences may be camera artefacts."
            ),
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "comparison.json").write_text(
        json.dumps(comparison, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    flat_metrics = [{key: value for key, value in item.items() if key != "cycles"} for item in summaries]
    write_csv(output_dir / "comparison_metrics.csv", flat_metrics)
    write_csv(output_dir / "comparison_trajectories.csv", trajectories)
    figure_path = output_dir / "motion_comparison.png"
    render_figure(figure_path, summaries, trajectories)
    report_path = output_dir / "comparison_report.md"
    report_path.write_text(build_markdown(comparison, figure_path.name), encoding="utf-8")
    artifact_path = output_dir / "artifact.json"
    artifact_path.write_text(
        json.dumps(build_portable_artifact(comparison, trajectories), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Decision: {comparison['status']}")
    print(f"Rapport: {report_path}")
    print(f"Figure: {figure_path}")
    print(f"Artifact HTML source: {artifact_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
