"""Crash-safe, dependency-aware checkpoints for V2 jobs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import UUID


CHECKPOINT_VERSION = "1.0"
TERMINAL_STATES = {"completed", "failed", "cancelled"}


@dataclass(frozen=True)
class JobCheckpoint:
    """Durable state for one resumable pipeline stage."""

    project_id: str
    job_id: str
    stage: str
    state: str
    sequence: int
    dependencies: tuple[str, ...]
    completed_artifacts: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None
    updated_at: str = ""
    checkpoint_version: str = CHECKPOINT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_version": self.checkpoint_version,
            "project_id": self.project_id,
            "job_id": self.job_id,
            "stage": self.stage,
            "state": self.state,
            "sequence": self.sequence,
            "dependencies": list(self.dependencies),
            "completed_artifacts": list(self.completed_artifacts),
            "metadata": dict(self.metadata or {}),
            "updated_at": self.updated_at,
        }


def checkpoint_path(root: Path, project_id: UUID | str, job_id: str, stage: str) -> Path:
    """Return the project-relative checkpoint path after validating identifiers."""
    for value, name in ((str(project_id), "project"), (job_id, "job"), (stage, "stage")):
        if not value or Path(value).name != value or value in {".", ".."}:
            raise ValueError(f"invalid {name} checkpoint identifier")
    path = root.expanduser().resolve() / "projects" / str(project_id) / "checkpoints" / f"{job_id}-{stage}.json"
    project_root = (root.expanduser().resolve() / "projects" / str(project_id)).resolve()
    if project_root not in path.parents:
        raise ValueError("checkpoint path escapes project root")
    return path


def write_checkpoint(path: Path, checkpoint: JobCheckpoint) -> Path:
    """Persist a checkpoint atomically so restart never observes a partial JSON file."""
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = checkpoint.to_dict()
    if not checkpoint.updated_at:
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def load_checkpoint(path: Path) -> JobCheckpoint:
    """Load and validate a checkpoint from disk."""
    payload = json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))
    if payload.get("checkpoint_version") != CHECKPOINT_VERSION:
        raise ValueError("unsupported checkpoint version")
    if payload.get("state") in TERMINAL_STATES and not payload.get("updated_at"):
        raise ValueError("terminal checkpoint must include updated_at")
    return JobCheckpoint(
        project_id=str(payload["project_id"]),
        job_id=str(payload["job_id"]),
        stage=str(payload["stage"]),
        state=str(payload["state"]),
        sequence=int(payload["sequence"]),
        dependencies=tuple(str(item) for item in payload.get("dependencies", [])),
        completed_artifacts=tuple(str(item) for item in payload.get("completed_artifacts", [])),
        metadata=dict(payload.get("metadata", {})),
        updated_at=str(payload.get("updated_at", "")),
    )


def dependencies_ready(checkpoint: JobCheckpoint, completed_stages: set[str]) -> bool:
    """Return whether all prerequisite stages have reached completion."""
    return all(stage in completed_stages for stage in checkpoint.dependencies)
