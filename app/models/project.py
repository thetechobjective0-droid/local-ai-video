"""Canonical project schema."""

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ProjectStatus(StrEnum):
    CREATED = "created"
    BRIEF_READY = "brief_ready"
    SCRIPT_READY = "script_ready"
    STORYBOARD_READY = "storyboard_ready"
    ASSETS_GENERATING = "assets_generating"
    ASSETS_READY = "assets_ready"
    FAILED = "failed"


class VideoProject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    schema_version: str = "1.1"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_prompt: str = Field(min_length=1)
    title: str = "Untitled Video"
    language: str = "en"
    target_audience: str = "general audience"
    tone: str = "informative"
    duration_seconds: float = Field(gt=0)
    aspect_ratio: str = "16:9"
    resolution: str = "1920x1080"
    fps: int = Field(default=30, ge=1, le=120)
    style: str = "cinematic"
    quality_profile: str = Field(default="balanced", pattern="^(fast|balanced|quality)$")
    status: ProjectStatus = ProjectStatus.CREATED
