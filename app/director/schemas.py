"""Script and storyboard schemas."""

import re

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.scene import Scene


class Script(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    narration: str = Field(min_length=1)
    estimated_duration_seconds: float = Field(gt=0)


def estimate_narration_seconds(text: str, words_per_minute: float = 150.0) -> float:
    """Estimate spoken duration from word count for deterministic timing checks."""
    if words_per_minute <= 0:
        raise ValueError("words per minute must be positive")
    word_count = len(re.findall(r"\S+", text))
    return word_count / words_per_minute * 60.0


def validate_script_duration(
    script: Script,
    target_duration_seconds: float,
    tolerance_ratio: float = 0.25,
) -> None:
    """Ensure the model's explicit script duration matches the project target."""
    if target_duration_seconds <= 0 or tolerance_ratio < 0:
        raise ValueError("target duration must be positive and tolerance ratio non-negative")
    lower = target_duration_seconds * (1 - tolerance_ratio)
    upper = target_duration_seconds * (1 + tolerance_ratio)
    if not lower <= script.estimated_duration_seconds <= upper:
        raise ValueError("script estimated duration is incompatible with target duration")


class Storyboard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenes: list[Scene] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_timeline(self) -> "Storyboard":
        ordered = sorted(self.scenes, key=lambda scene: scene.index)
        if [scene.index for scene in ordered] != list(range(1, len(ordered) + 1)):
            raise ValueError("scene indexes must be contiguous starting at 1")
        previous_end = 0.0
        for scene in ordered:
            if scene.start_seconds < previous_end - 1e-6:
                raise ValueError("scene intervals must not overlap")
            if scene.duration_seconds <= 0:
                raise ValueError("scene duration must be positive")
            if scene.subtitle_range is not None:
                subtitle_start, subtitle_end = scene.subtitle_range
                if subtitle_start < 0 or subtitle_end <= subtitle_start:
                    raise ValueError("subtitle range must be positive and ordered")
                if (
                    subtitle_start < scene.start_seconds - 1e-6
                    or subtitle_end > scene.start_seconds + scene.duration_seconds + 1e-6
                ):
                    raise ValueError("subtitle range must remain inside scene interval")
            previous_end = scene.start_seconds + scene.duration_seconds
        return self


def validate_storyboard_duration(
    storyboard: Storyboard,
    target_duration_seconds: float,
    tolerance_seconds: float = 0.5,
) -> None:
    """Ensure the storyboard ends at the requested project duration."""
    if target_duration_seconds <= 0 or tolerance_seconds < 0:
        raise ValueError("target duration must be positive and tolerance non-negative")
    end = max(scene.start_seconds + scene.duration_seconds for scene in storyboard.scenes)
    if abs(end - target_duration_seconds) > tolerance_seconds:
        raise ValueError(f"storyboard ends at {end:.3f}s; target is {target_duration_seconds:.3f}s")
