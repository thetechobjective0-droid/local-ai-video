"""Persistence helpers for generation-run metadata."""

from pathlib import Path

from app.models.run import GenerationRun
from app.storage.filesystem import FilesystemStore


class GenerationRunStore:
    """Persist one immutable-ish JSON record per generation attempt."""

    def __init__(self, store: FilesystemStore) -> None:
        self.store = store

    def save(self, directory: Path, run: GenerationRun) -> Path:
        """Atomically persist a generation run below the project directory."""
        runs_dir = directory / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        return self.store.write_json(runs_dir, f"{run.run_id}.json", run.model_dump(mode="json"))
