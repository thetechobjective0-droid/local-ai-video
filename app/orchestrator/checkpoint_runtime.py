"""Reusable checkpoint lifecycle for persistent V2 pipeline jobs."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from app.orchestrator.checkpoints import (
    JobCheckpoint,
    checkpoint_path,
    dependencies_ready,
    load_checkpoint,
    write_checkpoint,
)


class CheckpointRuntime:
    """Persist and resume ordered stages without rerunning completed work."""

    def __init__(self, root: Path, project_id: UUID | str, job_id: UUID | str) -> None:
        self.root = root
        self.project_id = project_id
        self.job_id = str(job_id)

    def load(self, stage: str) -> JobCheckpoint | None:
        path = checkpoint_path(self.root, self.project_id, self.job_id, stage)
        if not path.is_file():
            return None
        return load_checkpoint(path)

    def begin(
        self,
        stage: str,
        sequence: int,
        dependencies: tuple[str, ...] = (),
        *,
        metadata: dict[str, object] | None = None,
    ) -> JobCheckpoint:
        """Create or validate a running checkpoint before expensive work starts."""
        existing = self.load(stage)
        if existing is not None and existing.state == "completed":
            return existing
        completed = {
            candidate.stage
            for candidate in self._all()
            if candidate.state == "completed"
        }
        if not dependencies_ready(
            JobCheckpoint(
                project_id=str(self.project_id),
                job_id=self.job_id,
                stage=stage,
                state="running",
                sequence=sequence,
                dependencies=dependencies,
            ),
            completed,
        ):
            raise RuntimeError(f"checkpoint dependencies not ready for stage: {stage}")
        checkpoint = JobCheckpoint(
            project_id=str(self.project_id),
            job_id=self.job_id,
            stage=stage,
            state="running",
            sequence=sequence,
            dependencies=dependencies,
            completed_artifacts=existing.completed_artifacts if existing else (),
            metadata=metadata or (existing.metadata if existing else {}),
        )
        return write_checkpoint(
            checkpoint_path(self.root, self.project_id, self.job_id, stage), checkpoint
        ) and checkpoint

    def complete(
        self,
        stage: str,
        *,
        artifacts: tuple[str, ...] = (),
        metadata: dict[str, object] | None = None,
    ) -> JobCheckpoint:
        """Atomically record a completed stage and its durable artifacts."""
        existing = self.load(stage)
        if existing is None:
            raise ValueError(f"cannot complete unknown checkpoint stage: {stage}")
        checkpoint = JobCheckpoint(
            project_id=existing.project_id,
            job_id=existing.job_id,
            stage=existing.stage,
            state="completed",
            sequence=existing.sequence,
            dependencies=existing.dependencies,
            completed_artifacts=tuple(dict.fromkeys((*existing.completed_artifacts, *artifacts))),
            metadata=metadata if metadata is not None else existing.metadata,
        )
        write_checkpoint(checkpoint_path(self.root, self.project_id, self.job_id, stage), checkpoint)
        return checkpoint

    def should_skip(self, stage: str) -> bool:
        checkpoint = self.load(stage)
        return checkpoint is not None and checkpoint.state == "completed"

    def _all(self) -> list[JobCheckpoint]:
        directory = self.root.expanduser().resolve() / "projects" / str(self.project_id) / "checkpoints"
        result: list[JobCheckpoint] = []
        if not directory.is_dir():
            return result
        for path in directory.glob(f"{self.job_id}-*.json"):
            try:
                result.append(load_checkpoint(path))
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return result
