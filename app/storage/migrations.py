"""Idempotent filesystem schema migrations."""

from __future__ import annotations

import json
from pathlib import Path

CURRENT_SCHEMA_VERSION = "1.1"


def migrate_storage(root: Path) -> int:
    """Upgrade legacy project manifests to the current schema without changing media."""
    root = root.expanduser().resolve()
    migrated = 0
    projects = root / "projects"
    if not projects.is_dir():
        return 0
    for directory in projects.iterdir():
        if not directory.is_dir():
            continue
        project = directory / "project.json"
        if not project.is_file():
            continue
        try:
            data = json.loads(project.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if data.get("schema_version") == CURRENT_SCHEMA_VERSION:
            continue
        data["schema_version"] = CURRENT_SCHEMA_VERSION
        _atomic_json(project, data)
        migrated += 1
    return migrated


def _atomic_json(path: Path, data: dict[str, object]) -> None:
    temporary = path.with_name(f".{path.name}.migration-tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)
