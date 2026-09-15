from dataclasses import dataclass, field
from typing import Any

from app.director.brief import CreativeBrief
from app.director.director import build_brief
from app.providers.base import LLMRequest, LLMResponse


@dataclass
class CapturingProvider:
    response: str
    requests: list[LLMRequest] = field(default_factory=list)

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(text=self.response, model="fake")


def test_structured_generation_sends_pydantic_schema_to_provider() -> None:
    provider = CapturingProvider(
        '{"title":"AI Agents","objective":"Explain agents","audience":"Beginners",'
        '"tone":"clear","language":"en","duration_seconds":60,'
        '"visual_style":"cinematic"}'
    )

    result = build_brief(provider, "Explain AI agents", 60, "cinematic")

    assert isinstance(result, CreativeBrief)
    assert len(provider.requests) == 1
    request = provider.requests[0]
    assert isinstance(request.format, dict)
    schema: dict[str, Any] = request.format
    assert schema["type"] == "object"
    assert set(schema["required"]) == {
        "title",
        "objective",
        "audience",
        "tone",
        "language",
        "duration_seconds",
        "visual_style",
    }


def test_structured_repair_also_uses_schema_constraint() -> None:
    @dataclass
    class RepairProvider:
        responses: list[str]
        requests: list[LLMRequest] = field(default_factory=list)

        def generate(self, request: LLMRequest) -> LLMResponse:
            self.requests.append(request)
            return LLMResponse(text=self.responses.pop(0), model="fake")

    provider = RepairProvider(
        [
            '{"title":"AI"}',
            '{"title":"AI","objective":"Explain agents","audience":"general",'
            '"tone":"clear","language":"en","duration_seconds":30,"visual_style":"simple"}',
        ]
    )

    result = build_brief(provider, "Explain AI agents", 30, "simple")

    assert result.title == "AI"
    assert len(provider.requests) == 2
    assert all(isinstance(request.format, dict) for request in provider.requests)
    assert provider.requests[0].format == provider.requests[1].format
