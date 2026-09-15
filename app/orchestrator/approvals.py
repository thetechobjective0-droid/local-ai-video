"""Durable human approval checkpoints for expensive local stages."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ApprovalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: UUID
    stage: str = Field(min_length=1, max_length=100)
    status: str = Field(pattern="^(pending|approved|rejected)$")
    updated_at: datetime
    note: str | None = None


def _path(root: Path, project_id: UUID, stage: str) -> Path:
    if not stage.replace("-", "").replace("_", "").isalnum():
        raise ValueError("invalid approval stage")
    directory = (root.expanduser().resolve() / "projects" / str(project_id) / "approvals").resolve()
    directory.mkdir(parents=True, exist_ok=True)
    path = (directory / f"{stage}.json").resolve()
    if directory not in path.parents:
        raise ValueError("approval path escapes project directory")
    return path


def get_approval(root: Path, project_id: UUID, stage: str) -> ApprovalRecord | None:
    path = _path(root, project_id, stage)
    if not path.is_file():
        return None
    return ApprovalRecord.model_validate_json(path.read_text(encoding="utf-8"))


def set_approval(
    root: Path, project_id: UUID, stage: str, status: str, *, note: str | None = None
) -> ApprovalRecord:
    record = ApprovalRecord(
        project_id=project_id,
        stage=stage,
        status=status,
        updated_at=datetime.now(timezone.utc),
        note=note,
    )
    path = _path(root, project_id, stage)
    payload = record.model_dump_json(indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temp:
        temp.write(payload)
        temp_path = Path(temp.name)
    temp_path.replace(path)
    return record
