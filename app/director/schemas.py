"""Script and storyboard schemas."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.scene import Scene


class Script(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    narration: str = Field(min_length=1)
    estimated_duration_seconds: float = Field(gt=0)


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
    end = max(
        scene.start_seconds + scene.duration_seconds for scene in storyboard.scenes
    )
    if abs(end - target_duration_seconds) > tolerance_seconds:
        raise ValueError(
            f"storyboard ends at {end:.3f}s; target is {target_duration_seconds:.3f}s"
        )
