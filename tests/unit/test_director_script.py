from dataclasses import dataclass

from app.director.brief import CreativeBrief
from app.director.director import build_script
from app.director.schemas import Script
from app.providers.base import LLMRequest, LLMResponse


@dataclass
class FakeProvider:
    response: str

    def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(text=self.response, model="fake")


def test_create_script_from_brief() -> None:
    provider = FakeProvider(
        '{"title":"AI","narration":"AI agents plan and act.","estimated_duration_seconds":5}'
    )
    brief = CreativeBrief(
        title="AI",
        objective="Explain",
        audience="general",
        tone="clear",
        language="en",
        duration_seconds=5,
        visual_style="clean",
    )
    result = build_script(provider, brief)
    assert isinstance(result, Script)
    assert result.estimated_duration_seconds == 5
