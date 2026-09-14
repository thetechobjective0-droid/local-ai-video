"""Provider contracts for local text-to-speech backends."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class TTSRequest:
    text: str
    output_path: Path
    voice: str | None = None
    rate: int = 180
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class TTSResult:
    path: Path
    provider: str
    model: str
    voice: str | None
    duration_seconds: float
    sample_rate: int
    channels: int
    sha256: str
    metadata: dict[str, object] = field(default_factory=dict)


class TTSProvider(Protocol):
    def synthesize(self, request: TTSRequest) -> TTSResult: ...
