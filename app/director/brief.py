"""Validated creative brief schema."""

from pydantic import BaseModel, ConfigDict, Field


class CreativeBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    tone: str = Field(min_length=1)
    language: str = Field(min_length=2, max_length=20)
    duration_seconds: float = Field(gt=0)
    visual_style: str = Field(min_length=1)
