"""Provider contracts for local image-to-video backends."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class VideoGenerationRequest:
    """Inputs required to animate a local still image."""

    image_path: Path
    output_path: Path
    prompt: str = ""
    negative_prompt: str = ""
    duration_seconds: float = 4.0
    fps: int = 16
    seed: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class VideoResult:
    """Metadata returned by a local video provider."""

    path: Path
    provider: str
    model: str
    duration_seconds: float
    fps: int
    width: int
    height: int
    sha256: str
    metadata: dict[str, object] = field(default_factory=dict)


class VideoProvider(Protocol):
    """Protocol implemented by local image-to-video providers."""

    def generate(self, request: VideoGenerationRequest) -> VideoResult: ...
