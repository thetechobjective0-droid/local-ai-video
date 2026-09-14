"""Provider contract for local text-to-image generation."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ImageGenerationRequest:
    prompt: str
    negative_prompt: str = ""
    output_path: Path = Path("image.png")
    model: str | None = None
    width: int = 1024
    height: int = 576
    steps: int = 30
    guidance_scale: float = 7.0
    seed: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ImageResult:
    path: Path
    model: str
    provider: str
    width: int
    height: int
    seed: int | None
    sha256: str
    metadata: dict[str, object] = field(default_factory=dict)


class ImageProvider(Protocol):
    """Generate an image using a locally installed model/runtime."""

    def generate(self, request: ImageGenerationRequest) -> ImageResult: ...
