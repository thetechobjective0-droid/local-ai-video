"""Canonical deterministic timeline schema."""

from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TimelineScene(BaseModel):
    """One scene's resolved timing and media references."""

    model_config = ConfigDict(extra="forbid")

    scene_id: UUID
    index: int = Field(ge=1)
    start_seconds: float = Field(ge=0)
    duration_seconds: float = Field(gt=0)
    narration: str = ""
    image_asset: UUID | None = None
    video_asset: UUID | None = None
    audio_asset: UUID | None = None
    subtitle_start_seconds: float | None = None
    subtitle_end_seconds: float | None = None
    transition: str = "cut"
    motion: str | None = None


class Timeline(BaseModel):
    """Resolved project timeline consumed by deterministic render stages."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    project_id: UUID
    duration_seconds: float = Field(gt=0)
    fps: int = Field(ge=1, le=120)
    resolution: str = "1920x1080"
    aspect_ratio: str = "16:9"
    scenes: list[TimelineScene]
    subtitle_format: str = "srt"
    output_video: Path = Path("final.mp4")
    metadata: dict[str, object] = Field(default_factory=dict)
