"""Canonical scene schema."""

from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class SceneStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


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
    status: SceneStatus = SceneStatus.PENDING
