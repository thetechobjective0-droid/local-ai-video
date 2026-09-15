import json
from pathlib import Path

from app.storage.migrations import CURRENT_SCHEMA_VERSION, migrate_storage


def test_migrate_storage_updates_legacy_project_and_is_idempotent(tmp_path: Path) -> None:
    project = tmp_path / "projects" / "abc"
    project.mkdir(parents=True)
    path = project / "project.json"
    path.write_text(json.dumps({"id": "abc", "source_prompt": "demo"}), encoding="utf-8")

    assert migrate_storage(tmp_path) == 1
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == CURRENT_SCHEMA_VERSION
    assert migrate_storage(tmp_path) == 0
