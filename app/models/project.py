"""Canonical project schema."""

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ProjectStatus(StrEnum):
    CREATED = "created"
    FAILED = "failed"


class VideoProject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    schema_version: str = "1.0"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_prompt: str = Field(min_length=1)
    title: str = "Untitled Video"
    language: str = "en"
    duration_seconds: float = Field(gt=0)
    aspect_ratio: str = "16:9"
    resolution: str = "1920x1080"
    style: str = "balanced"
    status: ProjectStatus = ProjectStatus.CREATED
