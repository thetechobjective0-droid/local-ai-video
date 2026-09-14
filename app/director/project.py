"""Director project planning service."""

from datetime import datetime, timezone
from pathlib import Path

from app.director.director import build_brief, build_script, build_storyboard
from app.models.project import ProjectStatus, VideoProject
from app.providers.base import LLMProvider
from app.storage.filesystem import FilesystemStore


def _save_status(store: FilesystemStore, directory: Path, project: VideoProject,
                 status: ProjectStatus) -> None:
    project.status = status
    project.updated_at = datetime.now(timezone.utc)
    store.write_json(directory, "project.json", project.model_dump(mode="json"))


def create_plan(
    provider: LLMProvider,
    store: FilesystemStore,
    prompt: str,
    duration_seconds: float,
    style: str,
    aspect_ratio: str = "16:9",
    *,
    model: str | None = None,
    temperature: float = 0.2,
    top_p: float = 0.9,
    top_k: int = 40,
    quality_profile: str = "balanced",
) -> Path:
    """Create a project first, then persist each validated Director stage."""
    project = VideoProject(
        source_prompt=prompt,
        duration_seconds=duration_seconds,
        aspect_ratio=aspect_ratio,
        style=style,
        quality_profile=quality_profile,
    )
    directory = store.create_project(project)
    try:
        brief = build_brief(provider, prompt, duration_seconds, style,
                            model=model, temperature=temperature, top_p=top_p, top_k=top_k)
        project.title = brief.title
        project.language = brief.language
        project.target_audience = brief.audience
        project.tone = brief.tone
        store.write_json(directory, "brief.json", brief.model_dump(mode="json"))
        _save_status(store, directory, project, ProjectStatus.BRIEF_READY)

        script = build_script(provider, brief, model=model, temperature=temperature,
                              top_p=top_p, top_k=top_k)
        store.write_json(directory, "script.json", script.model_dump(mode="json"))
        _save_status(store, directory, project, ProjectStatus.SCRIPT_READY)

        storyboard = build_storyboard(provider, brief, script, model=model,
                                      temperature=temperature, top_p=top_p, top_k=top_k)
        store.write_json(directory, "storyboard.json", storyboard.model_dump(mode="json"))
        _save_status(store, directory, project, ProjectStatus.STORYBOARD_READY)
    except Exception:
        _save_status(store, directory, project, ProjectStatus.FAILED)
        raise
    return directory
