from dataclasses import dataclass

import pytest

from app.director.brief import CreativeBrief
from app.director.director import build_brief, build_script, build_storyboard
from app.providers.base import LLMRequest, LLMResponse


@dataclass
class FakeProvider:
    responses: list[str]

    def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(text=self.responses.pop(0), model="fake")


def test_build_brief_repairs_invalid_json() -> None:
    provider = FakeProvider(
        [
            "not json",
            '{"title":"AI","objective":"Explain agents","audience":"general","tone":"clear","language":"en","duration_seconds":60,"visual_style":"cinematic"}',
        ]
    )
    result = build_brief(provider, "Explain AI agents", 60, "cinematic")
    assert isinstance(result, CreativeBrief)


def test_build_script() -> None:
    provider = FakeProvider(
        ['{"title":"AI","narration":"AI agents plan and act.","estimated_duration_seconds":5}']
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
    assert result.estimated_duration_seconds == 5


def test_build_storyboard_rejects_overlap_after_repair() -> None:
    provider = FakeProvider(
        [
            '{"scenes":[{"index":1,"start_seconds":0,"duration_seconds":5,"narration":"one","visual_description":"one","image_prompt":"one","motion_prompt":"one"},{"index":2,"start_seconds":4,"duration_seconds":5,"narration":"two","visual_description":"two","image_prompt":"two","motion_prompt":"two"}]}',
            '{"scenes":[{"index":1,"start_seconds":0,"duration_seconds":5,"narration":"one","visual_description":"one","image_prompt":"one","motion_prompt":"one"},{"index":2,"start_seconds":5,"duration_seconds":5,"narration":"two","visual_description":"two","image_prompt":"two","motion_prompt":"two"}]}',
        ]
    )
    brief = CreativeBrief(
        title="AI",
        objective="Explain",
        audience="general",
        tone="clear",
        language="en",
        duration_seconds=10,
        visual_style="clean",
    )
    script = type("S", (), {})()
    # Use the real Script schema to keep the test boundary identical to production.
    from app.director.schemas import Script

    script = Script(title="AI", narration="one two", estimated_duration_seconds=10)
    result = build_storyboard(provider, brief, script)
    assert len(result.scenes) == 2
    assert result.scenes[1].start_seconds == 5
