"""Artifact metadata schema."""

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class Artifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    type: str = Field(min_length=1)
    path: Path
    mime: str = "application/octet-stream"
    provider: str = "local"
    model: str = "unknown"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sha256: str | None = None
    status: str = "created"
