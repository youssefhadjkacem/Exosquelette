"""Migrate legacy MyoConverter XML to MuJoCo 3.6 without editing the source artifact."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_ROOT))
from pipeline_utils import PROJECT_ROOT, dump_json, resolve_project_path  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--keep-unlimited-joints", action="store_true")
    args = parser.parse_args(argv)
    source, output = resolve_project_path(args.input), resolve_project_path(args.output)
    text = source.read_text(encoding="utf-8")
    changes = []
    migrated, count = re.subn(r'\s+collision="(?:predefined|dynamic)"', "", text)
    if count:
        changes.append(f"suppression de {count} attribut(s) option@collision obsolete(s)")
    if not args.keep_unlimited_joints:
        migrated, count = re.subn(
            r'(<joint\b[^>]*\brange="[^"]+"[^>]*\blimited=")false("[^>]*/>)',
            r"\1true\2", migrated,
        )
        if not count:
            # Covers XML where limited appears before range, as in current MyoConverter output.
            migrated, count = re.subn(
                r'(<joint\b[^>]*\blimited=")false("[^>]*\brange="[^"]+"[^>]*/>)',
                r"\1true\2", migrated,
            )
        if count:
            changes.append(f"activation de {count} limite(s) articulaire(s)")
    if not changes:
        print("Aucune migration necessaire.")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(migrated, encoding="utf-8")
    def portable(path: Path) -> str:
        try:
            return path.relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            return str(path)
    report = {
        "schema_version": 1, "source": portable(source),
        "output": portable(output), "changes": changes,
    }
    dump_json(output.with_suffix(".migration.json"), report)
    print(f"XML migre: {output}")
    for change in changes:
        print(f"- {change}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
