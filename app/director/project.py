"""Director project planning and resume services."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, TypeVar
import logging

from pydantic import BaseModel

from app.director.brief import CreativeBrief
from app.director.director import build_brief, build_script, build_storyboard
from app.director.schemas import Script, Storyboard
from app.models.project import ProjectStatus, VideoProject
from app.models.run import GenerationRun
from app.providers.base import LLMProvider
from app.storage.filesystem import FilesystemStore
from app.storage.runs import GenerationRunStore

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _save_status(
    store: FilesystemStore, directory: Path, project: VideoProject, status: ProjectStatus
) -> None:
    project.status = status
    project.updated_at = datetime.now(timezone.utc)
    store.write_json(directory, "project.json", project.model_dump(mode="json"))
    logger.info("[director] project=%s status=%s", project.id, status.value)


def _run_stage(
    store: FilesystemStore,
    directory: Path,
    project: VideoProject,
    stage: str,
    provider: LLMProvider,
    model: str | None,
    parameters: dict[str, object],
    input_data: dict[str, object],
    operation: Callable[[], T],
    output_artifacts: list[str],
) -> T:
    """Execute one Director stage and persist its lifecycle metadata."""
    logger.info(
        "[director] stage=%s START project=%s provider=%s model=%s",
        stage,
        project.id,
        provider.__class__.__name__,
        model or "provider-default",
    )
    run = GenerationRun(
        project_id=project.id,
        stage=stage,
        provider=provider.__class__.__name__,
        model=model or "provider-default",
        input=input_data,
        parameters=parameters,
    )
    runs = GenerationRunStore(store)
    runs.save(directory, run)
    try:
        result = operation()
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
        run.completed_at = datetime.now(timezone.utc)
        runs.save(directory, run)
        logger.exception("[director] stage=%s FAILED project=%s error=%s", stage, project.id, exc)
        raise
    run.status = "completed"
    run.completed_at = datetime.now(timezone.utc)
    run.output_artifacts = output_artifacts
    runs.save(directory, run)
    logger.info(
        "[director] stage=%s COMPLETE project=%s artifacts=%s",
        stage,
        project.id,
        ",".join(output_artifacts),
    )
    return result


def _parameters(temperature: float, top_p: float, top_k: int) -> dict[str, object]:
    return {"temperature": temperature, "top_p": top_p, "top_k": top_k}


def _load_artifact(directory: Path, filename: str, model: type[T]) -> T | None:
    path = directory / filename
    if not path.is_file():
        logger.info("[director] artifact missing file=%s", filename)
        return None
    try:
        artifact = model.model_validate_json(path.read_text(encoding="utf-8"))
        logger.info("[director] artifact valid file=%s", filename)
        return artifact
    except Exception as exc:
        logger.warning("[director] artifact invalid file=%s error=%s", filename, exc)
        return None


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
    logger.info(
        "[director] create_plan prompt_chars=%s duration=%ss style=%s aspect_ratio=%s",
        len(prompt),
        duration_seconds,
        style,
        aspect_ratio,
    )
    project = VideoProject(
        source_prompt=prompt,
        duration_seconds=duration_seconds,
        aspect_ratio=aspect_ratio,
        style=style,
        quality_profile=quality_profile,
    )
    directory = store.create_project(project)
    logger.info("[director] project created id=%s directory=%s", project.id, directory)
    return _run_plan(
        provider,
        store,
        directory,
        project,
        model=model,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        start_from="brief",
    )


def resume_plan(
    provider: LLMProvider,
    store: FilesystemStore,
    project_id: str,
    *,
    model: str | None = None,
    temperature: float = 0.2,
    top_p: float = 0.9,
    top_k: int = 40,
) -> Path:
    """Resume a project from the first missing or invalid Director artifact."""
    directory = store.project_dir(project_id)
    project = store.load_project(project_id)
    logger.info("[director] resume project=%s current_status=%s", project.id, project.status.value)
    if not directory.is_dir():
        raise FileNotFoundError(f"project directory does not exist: {project_id}")
    if project.status == ProjectStatus.STORYBOARD_READY and _load_artifact(
        directory, "storyboard.json", Storyboard
    ):
        logger.info("[director] resume project=%s already storyboard_ready", project.id)
        return directory
    start_from = "brief"
    if _load_artifact(directory, "brief.json", CreativeBrief):
        start_from = "script"
        if _load_artifact(directory, "script.json", Script):
            start_from = "storyboard"
    logger.info("[director] resume project=%s start_from=%s", project.id, start_from)
    return _run_plan(
        provider,
        store,
        directory,
        project,
        model=model,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        start_from=start_from,
    )


def _run_plan(
    provider: LLMProvider,
    store: FilesystemStore,
    directory: Path,
    project: VideoProject,
    *,
    model: str | None,
    temperature: float,
    top_p: float,
    top_k: int,
    start_from: str,
) -> Path:
    params = _parameters(temperature, top_p, top_k)
    logger.info("[director] pipeline START project=%s start_from=%s", project.id, start_from)
    try:
        brief = _load_artifact(directory, "brief.json", CreativeBrief)
        if start_from == "brief" or brief is None:
            brief = _run_stage(
                store,
                directory,
                project,
                "brief",
                provider,
                model,
                params,
                {
                    "prompt": project.source_prompt,
                    "duration_seconds": project.duration_seconds,
                    "style": project.style,
                },
                lambda: build_brief(
                    provider,
                    project.source_prompt,
                    project.duration_seconds,
                    project.style,
                    model=model,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                ),
                ["brief.json"],
            )
            project.title = brief.title
            project.language = brief.language
            project.target_audience = brief.audience
            project.tone = brief.tone
            store.write_json(directory, "brief.json", brief.model_dump(mode="json"))
            logger.info("[director] brief persisted project=%s title=%r", project.id, brief.title)
            _save_status(store, directory, project, ProjectStatus.BRIEF_READY)

        script = _load_artifact(directory, "script.json", Script)
        if start_from in {"brief", "script"} or script is None:
            script = _run_stage(
                store,
                directory,
                project,
                "script",
                provider,
                model,
                params,
                {"brief": brief.model_dump(mode="json")},
                lambda: build_script(
                    provider, brief, model=model, temperature=temperature, top_p=top_p, top_k=top_k
                ),
                ["script.json"],
            )
            store.write_json(directory, "script.json", script.model_dump(mode="json"))
            logger.info("[director] script persisted project=%s", project.id)
            _save_status(store, directory, project, ProjectStatus.SCRIPT_READY)

        storyboard = _load_artifact(directory, "storyboard.json", Storyboard)
        if start_from in {"brief", "script", "storyboard"} or storyboard is None:
            storyboard = _run_stage(
                store,
                directory,
                project,
                "storyboard",
                provider,
                model,
                params,
                {"brief": brief.model_dump(mode="json"), "script": script.model_dump(mode="json")},
                lambda: build_storyboard(
                    provider,
                    brief,
                    script,
                    model=model,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                ),
                ["storyboard.json"],
            )
            store.write_json(directory, "storyboard.json", storyboard.model_dump(mode="json"))
            logger.info(
                "[director] storyboard persisted project=%s scenes=%s",
                project.id,
                len(storyboard.scenes),
            )
            _save_status(store, directory, project, ProjectStatus.STORYBOARD_READY)
    except Exception:
        logger.exception("[director] pipeline FAILED project=%s", project.id)
        _save_status(store, directory, project, ProjectStatus.FAILED)
        raise
    logger.info("[director] pipeline COMPLETE project=%s", project.id)
    return directory
