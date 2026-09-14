"""Provider contracts shared by local model adapters."""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class LLMRequest:
    prompt: str
    system: str | None = None
    model: str | None = None
    temperature: float = 0.2
    top_p: float = 0.9
    top_k: int = 40
    format: str | None = "json"


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    metadata: dict[str, object] = field(default_factory=dict)


class LLMProvider(Protocol):
    def generate(self, request: LLMRequest) -> LLMResponse: ...
