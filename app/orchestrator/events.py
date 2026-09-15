"""Append-only structured job event history for local operational replay."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

EVENT_VERSION = "1.0"
MAX_READ_EVENTS = 5000


@dataclass(frozen=True)
class JobEvent:
    """One durable event in a project's job history."""

    event: str
    project_id: UUID | str
    job_id: UUID | str | None = None
    stage: str | None = None
    state: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    sequence: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_version: str = EVENT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "project_id": str(self.project_id),
            "job_id": str(self.job_id) if self.job_id is not None else None,
            "stage": self.stage,
            "state": self.state,
            "details": self.details,
            "sequence": self.sequence,
            "timestamp": self.timestamp.astimezone(timezone.utc).isoformat(),
            "event_version": self.event_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "JobEvent":
        timestamp = datetime.fromisoformat(str(payload["timestamp"]))
        details = payload.get("details", {})
        if not isinstance(details, dict):
            raise ValueError("event details must be an object")
        return cls(
            event=str(payload["event"]),
            project_id=str(payload["project_id"]),
            job_id=str(payload["job_id"]) if payload.get("job_id") is not None else None,
            stage=str(payload["stage"]) if payload.get("stage") is not None else None,
            state=str(payload["state"]) if payload.get("state") is not None else None,
            details=details,
            sequence=int(payload.get("sequence", 0)),
            timestamp=timestamp,
            event_version=str(payload.get("event_version", "1.0")),
        )


def event_path(root: Path, project_id: UUID | str) -> Path:
    """Return a project-scoped append-only event stream path."""
    project_dir = (root.expanduser().resolve() / "projects" / str(project_id)).resolve()
    project_root = root.expanduser().resolve() / "projects"
    if project_root.resolve() not in project_dir.parents:
        raise ValueError("event path escapes project storage root")
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir / "events.jsonl"


def _next_sequence(path: Path) -> int:
    if not path.is_file():
        return 1
    last_sequence = 0
    try:
        with path.open("r", encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                payload = json.loads(line)
                last_sequence = max(last_sequence, int(payload.get("sequence", 0)))
    except (OSError, ValueError, TypeError, KeyError):
        return last_sequence + 1
    return last_sequence + 1


class JobEventLog:
    """Durable JSONL event stream with bounded replay."""

    def __init__(self, root: Path, project_id: UUID | str) -> None:
        self.root = root
        self.project_id = project_id

    @property
    def path(self) -> Path:
        return event_path(self.root, self.project_id)

    def append(
        self,
        event: str,
        *,
        job_id: UUID | str | None = None,
        stage: str | None = None,
        state: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> JobEvent:
        record = JobEvent(
            event=event,
            project_id=self.project_id,
            job_id=job_id,
            stage=stage,
            state=state,
            details=details or {},
            sequence=_next_sequence(self.path),
        )
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
            stream.flush()
        return record

    def read(self, *, limit: int = MAX_READ_EVENTS) -> list[JobEvent]:
        """Read the newest events without loading an unbounded history into memory."""
        if limit <= 0:
            return []
        records: list[JobEvent] = []
        if not self.path.is_file():
            return records
        try:
            with self.path.open("r", encoding="utf-8") as stream:
                for line in stream:
                    if not line.strip():
                        continue
                    try:
                        records.append(JobEvent.from_dict(json.loads(line)))
                    except (TypeError, ValueError, KeyError, json.JSONDecodeError):
                        continue
        except OSError:
            return records
        return records[-limit:]


def append_job_event(
    root: Path,
    project_id: UUID | str,
    event: str,
    *,
    job_id: UUID | str | None = None,
    stage: str | None = None,
    state: str | None = None,
    details: dict[str, Any] | None = None,
) -> JobEvent:
    """Convenience wrapper for one durable local event."""
    return JobEventLog(root, project_id).append(
        event,
        job_id=job_id,
        stage=stage,
        state=state,
        details=details,
    )
