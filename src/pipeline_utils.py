"""Shared utilities for the exoskeleton motion-processing pipeline."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AXES = ("x", "y", "z")


def resolve_project_path(value: str | Path) -> Path:
    """Resolve a CLI path relative to the project root."""
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_csv_rows(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"CSV sans en-tete: {path}")
        return list(reader.fieldnames), list(reader)


def write_csv_rows(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_float(value: object) -> float:
    if value is None or value == "":
        return math.nan
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def coordinate_markers(fieldnames: Sequence[str]) -> Dict[str, Dict[str, str]]:
    """Return marker -> axis -> column for columns ending in _x/_y/_z."""
    markers: Dict[str, Dict[str, str]] = {}
    for column in fieldnames:
        for axis in AXES:
            suffix = f"_{axis}"
            if column.endswith(suffix):
                marker = column[: -len(suffix)]
                markers.setdefault(marker, {})[axis] = column
                break
    return {name: axes for name, axes in markers.items() if set(axes) == set(AXES)}


def contiguous_ranges(mask: Sequence[bool]) -> Iterable[Tuple[int, int]]:
    """Yield half-open ranges containing consecutive True values."""
    start = None
    for index, value in enumerate([*mask, False]):
        if value and start is None:
            start = index
        elif not value and start is not None:
            yield start, index
            start = None


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def dump_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
