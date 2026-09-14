"""Director project planning and resume services."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, TypeVar
import logging

from pydantic import BaseModel

from app.director.brief import CreativeBrief
from app.director.director import build_brief, build_script, build_storyboard
from app.director.schemas import Script, Storyboard, validate_storyboard_duration
from app.models.project import ProjectStatus, VideoProject
from app.models.run import GenerationRun
from app.models.timeline import Timeline, TimelineScene
from app.providers.base import LLMProvider
from app.storage.filesystem import FilesystemStore
from app.storage.runs import GenerationRunStore

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


def _save_status(store: FilesystemStore, directory: Path, project: VideoProject, status: ProjectStatus) -> None:
    project.status = status
    project.updated_at = datetime.now(timezone.utc)
    store.write_json(directory, "project.json", project.model_dump(mode="json"))
    logger.info("[director] project=%s status=%s", project.id, status.value)


def _run_stage(store: FilesystemStore, directory: Path, project: VideoProject, stage: str, provider: LLMProvider, model: str | None, parameters: dict[str, object], input_data: dict[str, object], operation: Callable[[], T], output_artifacts: list[str]) -> T:
    logger.info("[director] stage=%s START project=%s provider=%s model=%s", stage, project.id, provider.__class__.__name__, model or "provider-default")
    run = GenerationRun(project_id=project.id, stage=stage, provider=provider.__class__.__name__, model=model or "provider-default", input=input_data, parameters=parameters)
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
    logger.info("[director] stage=%s COMPLETE project=%s artifacts=%s", stage, project.id, ",".join(output_artifacts))
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


def _subtitle_timestamp(seconds: float, *, vtt: bool = False) -> str:
    total_ms = max(0, round(seconds * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    separator = "." if vtt else ","
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millis:03d}"


def _persist_subtitles(directory: Path, storyboard: Storyboard) -> None:
    entries = [scene for scene in sorted(storyboard.scenes, key=lambda item: item.index) if scene.narration.strip()]
    srt_parts: list[str] = []
    vtt_parts: list[str] = ["WEBVTT", ""]
    for number, scene in enumerate(entries, start=1):
        start = scene.start_seconds
        end = scene.start_seconds + scene.duration_seconds
        text = scene.narration.strip()
        srt_parts.extend([str(number), f"{_subtitle_timestamp(start)} --> {_subtitle_timestamp(end)}", text, ""])
        vtt_parts.extend([f"{_subtitle_timestamp(start, vtt=True)} --> {_subtitle_timestamp(end, vtt=True)}", text, ""])
    (directory / "subtitles.srt").write_text("\n".join(srt_parts), encoding="utf-8")
    (directory / "subtitles.vtt").write_text("\n".join(vtt_parts), encoding="utf-8")
    logger.info("[director] subtitles persisted scenes=%s formats=srt,vtt", len(entries))


def _persist_storyboard_outputs(store: FilesystemStore, directory: Path, project: VideoProject, storyboard: Storyboard) -> None:
    logger.info("[director] materializing storyboard project=%s scenes=%s", project.id, len(storyboard.scenes))
    for scene in sorted(storyboard.scenes, key=lambda item: item.index):
        path = directory / f"scene-{scene.index:04d}.json"
        store.write_json(directory, path.name, scene.model_dump(mode="json"))
        logger.info("[director] scene manifest persisted project=%s index=%s id=%s", project.id, scene.index, scene.id)
    timeline_scenes = [TimelineScene(scene_id=scene.id, index=scene.index, start_seconds=scene.start_seconds, duration_seconds=scene.duration_seconds, narration=scene.narration, image_asset=scene.image_asset, video_asset=scene.video_asset, audio_asset=scene.audio_asset, subtitle_start_seconds=scene.subtitle_range[0] if scene.subtitle_range else None, subtitle_end_seconds=scene.subtitle_range[1] if scene.subtitle_range else None, motion=scene.motion_prompt or None) for scene in sorted(storyboard.scenes, key=lambda item: item.index)]
    timeline = Timeline(project_id=project.id, duration_seconds=project.duration_seconds, fps=project.fps, resolution=project.resolution, aspect_ratio=project.aspect_ratio, scenes=timeline_scenes, metadata={"generated_by": "director", "stage": "storyboard"})
    store.write_json(directory, "timeline.json", timeline.model_dump(mode="json"))
    _persist_subtitles(directory, storyboard)
    logger.info("[director] timeline persisted project=%s scenes=%s duration=%ss", project.id, len(timeline.scenes), timeline.duration_seconds)


def create_plan(provider: LLMProvider, store: FilesystemStore, prompt: str, duration_seconds: float, style: str, aspect_ratio: str = "16:9", *, model: str | None = None, temperature: float = 0.2, top_p: float = 0.9, top_k: int = 40, quality_profile: str = "balanced") -> Path:
    project = VideoProject(source_prompt=prompt, duration_seconds=duration_seconds, aspect_ratio=aspect_ratio, style=style, quality_profile=quality_profile)
    directory = store.create_project(project)
    logger.info("[director] project created id=%s directory=%s", project.id, directory)
    return _run_plan(provider, store, directory, project, model=model, temperature=temperature, top_p=top_p, top_k=top_k, start_from="brief")


def resume_plan(provider: LLMProvider, store: FilesystemStore, project_id: str, *, model: str | None = None, temperature: float = 0.2, top_p: float = 0.9, top_k: int = 40) -> Path:
    """Resume planning while invalidating artifacts tied to an old duration contract."""
    directory = store.project_dir(project_id)
    project = store.load_project(project_id)
    logger.info("[director] resume project=%s current_status=%s target_duration=%ss", project.id, project.status.value, project.duration_seconds)
    if not directory.is_dir():
        raise FileNotFoundError(f"project directory does not exist: {project_id}")
    brief = _load_artifact(directory, "brief.json", CreativeBrief)
    brief_matches_duration = brief is not None and abs(brief.duration_seconds - project.duration_seconds) < 1e-6
    if project.status == ProjectStatus.STORYBOARD_READY:
        storyboard = _load_artifact(directory, "storyboard.json", Storyboard)
        if storyboard is not None:
            try:
                validate_storyboard_duration(storyboard, project.duration_seconds)
            except ValueError as exc:
                logger.warning("[director] persisted storyboard invalid for target duration project=%s error=%s", project.id, exc)
                start_from = "brief" if not brief_matches_duration else "storyboard"
            else:
                _persist_storyboard_outputs(store, directory, project, storyboard)
                logger.info("[director] resume project=%s already storyboard_ready; outputs reconciled", project.id)
                return directory
        else:
            start_from = "storyboard" if brief_matches_duration else "brief"
    else:
        start_from = "brief" if not brief_matches_duration else "script"
        if brief_matches_duration and _load_artifact(directory, "script.json", Script):
            start_from = "storyboard"
    logger.info("[director] resume project=%s start_from=%s", project.id, start_from)
    return _run_plan(provider, store, directory, project, model=model, temperature=temperature, top_p=top_p, top_k=top_k, start_from=start_from)


def _run_plan(provider: LLMProvider, store: FilesystemStore, directory: Path, project: VideoProject, *, model: str | None, temperature: float, top_p: float, top_k: int, start_from: str) -> Path:
    params = _parameters(temperature, top_p, top_k)
    logger.info("[director] pipeline START project=%s start_from=%s target_duration=%ss", project.id, start_from, project.duration_seconds)
    try:
        brief = _load_artifact(directory, "brief.json", CreativeBrief)
        if start_from == "brief" or brief is None or abs(brief.duration_seconds - project.duration_seconds) >= 1e-6:
            brief = _run_stage(store, directory, project, "brief", provider, model, params, {"prompt": project.source_prompt, "duration_seconds": project.duration_seconds, "style": project.style}, lambda: build_brief(provider, project.source_prompt, project.duration_seconds, project.style, model=model, temperature=temperature, top_p=top_p, top_k=top_k), ["brief.json"])
            project.title = brief.title
            project.language = brief.language
            project.target_audience = brief.audience
            project.tone = brief.tone
            store.write_json(directory, "brief.json", brief.model_dump(mode="json"))
            logger.info("[director] brief persisted project=%s title=%r duration=%ss", project.id, brief.title, brief.duration_seconds)
            _save_status(store, directory, project, ProjectStatus.BRIEF_READY)
        script = _load_artifact(directory, "script.json", Script)
        if start_from in {"brief", "script"} or script is None:
            script = _run_stage(store, directory, project, "script", provider, model, params, {"brief": brief.model_dump(mode="json")}, lambda: build_script(provider, brief, model=model, temperature=temperature, top_p=top_p, top_k=top_k), ["script.json"])
            store.write_json(directory, "script.json", script.model_dump(mode="json"))
            logger.info("[director] script persisted project=%s", project.id)
            _save_status(store, directory, project, ProjectStatus.SCRIPT_READY)
        storyboard = _load_artifact(directory, "storyboard.json", Storyboard)
        if start_from in {"brief", "script", "storyboard"} or storyboard is None:
            storyboard = _run_stage(store, directory, project, "storyboard", provider, model, params, {"brief": brief.model_dump(mode="json"), "script": script.model_dump(mode="json")}, lambda: build_storyboard(provider, brief, script, model=model, temperature=temperature, top_p=top_p, top_k=top_k), ["storyboard.json"])
            store.write_json(directory, "storyboard.json", storyboard.model_dump(mode="json"))
            _persist_storyboard_outputs(store, directory, project, storyboard)
            logger.info("[director] storyboard persisted project=%s scenes=%s", project.id, len(storyboard.scenes))
            _save_status(store, directory, project, ProjectStatus.STORYBOARD_READY)
    except Exception:
        logger.exception("[director] pipeline FAILED project=%s", project.id)
        _save_status(store, directory, project, ProjectStatus.FAILED)
        raise
    logger.info("[director] pipeline COMPLETE project=%s", project.id)
    return directory
