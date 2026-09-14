"""Director project planning service."""

from pathlib import Path

from app.director.director import build_brief, build_script, build_storyboard
from app.models.project import VideoProject
from app.providers.base import LLMProvider
from app.storage.filesystem import FilesystemStore


def create_plan(
    provider: LLMProvider,
    store: FilesystemStore,
    prompt: str,
    duration_seconds: float,
    style: str,
    aspect_ratio: str = "16:9",
) -> Path:
    """Generate and persist the validated Director planning artifacts."""
    brief = build_brief(provider, prompt, duration_seconds, style)
    script = build_script(provider, brief)
    storyboard = build_storyboard(provider, brief, script)

    project = VideoProject(
        source_prompt=prompt,
        title=brief.title,
        language=brief.language,
        duration_seconds=duration_seconds,
        aspect_ratio=aspect_ratio,
        style=brief.visual_style,
    )
    directory = store.create_project(project)
    store.write_json(directory, "brief.json", brief.model_dump(mode="json"))
    store.write_json(directory, "script.json", script.model_dump(mode="json"))
    store.write_json(directory, "storyboard.json", storyboard.model_dump(mode="json"))
    return directory
