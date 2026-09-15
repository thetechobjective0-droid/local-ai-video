"""Tests for resumable Director planning and run metadata."""

from dataclasses import dataclass
from pathlib import Path

from app.director.project import create_plan, resume_plan
from app.models.project import ProjectStatus
from app.providers.base import LLMRequest, LLMResponse
from app.storage.filesystem import FilesystemStore


@dataclass
class CountingProvider:
    calls: int = 0

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        schema = request.format if isinstance(request.format, dict) else {}
        properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
        if "scenes" in properties:
            text = '{"scenes":[{"index":1,"start_seconds":0,"duration_seconds":5,"narration":"plan","visual_description":"planning","image_prompt":"planning","motion_prompt":"slow"},{"index":2,"start_seconds":5,"duration_seconds":5,"narration":"act","visual_description":"acting","image_prompt":"acting","motion_prompt":"slow"}]}'
        elif "estimated_duration_seconds" in properties:
            text = '{"title":"Agents","narration":"AI agents plan and act.","estimated_duration_seconds":10}'
        else:
            text = '{"title":"Agents","objective":"Explain agents","audience":"general","tone":"clear","language":"en","duration_seconds":10,"visual_style":"cinematic"}'
        return LLMResponse(text=text, model="fake")


def test_resume_completed_project_does_not_call_provider(tmp_path: Path) -> None:
    store = FilesystemStore(tmp_path, minimum_free_bytes=0)
    provider = CountingProvider()
    directory = create_plan(provider, store, "Explain agents", 10, "cinematic")
    assert provider.calls == 3

    resume_plan(provider, store, directory.name)
    assert provider.calls == 3
    assert store.load_project(directory.name).status == ProjectStatus.STORYBOARD_READY
    assert len(list((directory / "runs").glob("*.json"))) == 3


def test_resume_missing_storyboard_runs_only_storyboard(tmp_path: Path) -> None:
    store = FilesystemStore(tmp_path, minimum_free_bytes=0)
    provider = CountingProvider()
    directory = create_plan(provider, store, "Explain agents", 10, "cinematic")
    (directory / "storyboard.json").unlink()
    calls_before = provider.calls

    resume_plan(provider, store, directory.name)
    assert provider.calls == calls_before + 1
    assert (directory / "storyboard.json").exists()
    assert store.load_project(directory.name).status == ProjectStatus.STORYBOARD_READY

    run_files = list((directory / "runs").glob("*.json"))
    assert len(run_files) == 4
