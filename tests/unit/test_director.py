import pytest

from app.director.brief import CreativeBrief
from app.director.director import build_brief
from app.providers.base import LLMResponse


class FakeLLM:
    def __init__(self, text: str) -> None:
        self.text = text

    def generate(self, _request: object) -> LLMResponse:
        return LLMResponse(text=self.text, model="fake")


def test_director_validates_structured_brief() -> None:
    provider = FakeLLM(
        '{"title":"AI Agents","objective":"Explain agents","audience":"Beginners",'
        '"tone":"clear","language":"en","duration_seconds":60,'
        '"visual_style":"cinematic"}'
    )
    brief = build_brief(provider, "Explain AI agents", 60, "cinematic")
    assert isinstance(brief, CreativeBrief)
    assert brief.duration_seconds == 60


def test_director_rejects_non_json() -> None:
    with pytest.raises(ValueError, match="invalid JSON"):
        build_brief(FakeLLM("not json"), "test", 30, "simple")
