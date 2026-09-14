"""Canonical scene schema."""

from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class SceneStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class MediaType(StrEnum):
    STATIC_IMAGE = "static_image"
    IMAGE_MOTION = "image_motion"
    IMAGE_TO_VIDEO = "image_to_video"
    TEXT_TO_VIDEO = "text_to_video"


class SceneValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool = True
    issues: list[str] = Field(default_factory=list)


class Scene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    index: int = Field(ge=1)
    start_seconds: float = Field(ge=0)
    duration_seconds: float = Field(gt=0)
    narration: str = ""
    visual_description: str = ""
    image_prompt: str = ""
    motion_prompt: str = ""
    negative_prompt: str = ""
    camera: str = ""
    composition: str = ""
    lighting: str = ""
    style: str = ""
    characters: list[str] = Field(default_factory=list)
    subjects: list[str] = Field(default_factory=list)
    reference_assets: list[str] = Field(default_factory=list)
    preferred_media_type: MediaType = MediaType.STATIC_IMAGE
    fallback_media_type: MediaType = MediaType.IMAGE_MOTION
    image_asset: UUID | None = None
    video_asset: UUID | None = None
    audio_asset: UUID | None = None
    subtitle_range: tuple[float, float] | None = None
    validation: SceneValidation = Field(default_factory=SceneValidation)
    status: SceneStatus = SceneStatus.PENDING
    metadata: dict[str, object] = Field(default_factory=dict)
