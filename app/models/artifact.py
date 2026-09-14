"""Artifact metadata schema."""

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class Artifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    scene_id: UUID | None = None
    type: str = Field(min_length=1)
    path: Path
    mime: str = "application/octet-stream"
    provider: str = "local"
    model: str = "unknown"
    model_version: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sha256: str | None = None
    parameters: dict[str, object] = Field(default_factory=dict)
    input_artifacts: list[UUID] = Field(default_factory=list)
    status: str = "created"
