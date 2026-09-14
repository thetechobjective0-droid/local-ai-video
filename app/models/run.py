"""Generation run metadata schema."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class GenerationRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    scene_id: UUID | None = None
    stage: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    input: dict[str, object] = Field(default_factory=dict)
    parameters: dict[str, object] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    status: str = Field(default="running", min_length=1)
    error: str | None = None
    output_artifacts: list[str] = Field(default_factory=list)
