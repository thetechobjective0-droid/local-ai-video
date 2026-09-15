"""HTTP routes for local background jobs."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import load_config
from app.generation.audio import generate_scene_audio
from app.generation.image_recovery import generate_scene_image_with_recovery
from app.generation.video_recovery import generate_scene_video_with_recovery
from app.models.project import ProjectStatus, VideoProject
from app.models.scene import Scene
from app.orchestrator.jobs import MediaJobManager, _finalize_project_media, get_job_manager
from app.orchestrator.regeneration import clear_scene_stage_outputs, invalidate_scene_dependencies
from app.providers.diffusers_image import DiffusersImageProvider
from app.providers.factory import build_video_provider
from app.providers.macos_tts import MacOSTTSProvider
from app.storage.filesystem import FilesystemStore

router = APIRouter()


class CreateProjectRequest(BaseModel):
    """Validated request for asynchronous project creation."""

    model_config = {"extra": "forbid"}

    prompt: str = Field(min_length=1, max_length=20_000)
    duration: float = Field(default=60.0, gt=0, le=3600)
    style: str = Field(default="cinematic", min_length=1, max_length=200)
    aspect_ratio: str = Field(default="16:9", min_length=3, max_length=16)


class RegenerateSceneRequest(BaseModel):
    """Validated selective scene regeneration request."""

    model_config = {"extra": "forbid"}

    stage: str = Field(default="video", pattern="^(image|audio|video)$")


def _store() -> FilesystemStore:
    return FilesystemStore(load_config(None).storage.root)


def _manager() -> MediaJobManager:
    return get_job_manager(_store())


def _planning_manager():
    from app.orchestrator.planning_jobs import get_planning_job_manager

    return get_planning_job_manager(_store())


def _planning_job_response(store: FilesystemStore, job) -> dict[str, Any]:
    """Expose durable project completion over stale background-job state."""
    project = store.load_project(job.project_id)
    if project.status == ProjectStatus.STORYBOARD_READY and job.state != "completed":
        job = job.model_copy(
            update={"state": "completed", "completed_stage": "storyboard", "error": None}
        )
    return job.model_dump(mode="json")


def _scene(store: FilesystemStore, project_id: UUID, scene_id: UUID) -> Scene:
    for path in sorted(store.project_dir(project_id).glob("scene-*.json")):
        if path.name.endswith(("-image.json", "-audio.json", "-video.json")):
            continue
        try:
            scene = Scene.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if scene.id == scene_id:
            return scene
    raise HTTPException(status_code=404, detail="scene not found")


def _persist_scene(store: FilesystemStore, project_id: UUID, scene: Scene) -> None:
    store.write_json(
        store.project_dir(project_id),
        f"scene-{scene.index:04d}.json",
        scene.model_dump(mode="json"),
    )


@router.post("/api/projects/{project_id}/jobs/media", status_code=202)
def create_media_job(project_id: UUID) -> dict[str, Any]:
    """Queue media generation only after planning has produced scenes."""
    manager = _manager()
    try:
        job = manager.submit(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="project not found") from None
    except ValueError as exc:
        raise HTTPException(
            status_code=409, detail={"code": "planning_not_ready", "message": str(exc)}
        ) from exc
    return job.model_dump(mode="json")


@router.get("/api/jobs/{job_id}")
def get_media_job(job_id: UUID) -> dict[str, Any]:
    try:
        return _manager().get(job_id).model_dump(mode="json")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found") from None


@router.get("/api/projects/{project_id}/jobs")
def list_media_jobs(project_id: UUID) -> list[dict[str, Any]]:
    return [job.model_dump(mode="json") for job in _manager().list(project_id)]


@router.post("/api/projects/{project_id}/scenes/{scene_id}/regenerate")
def regenerate_scene(
    project_id: UUID, scene_id: UUID, request: RegenerateSceneRequest
) -> dict[str, Any]:
    """Regenerate a scene and every artifact downstream of the requested stage."""
    requested_stage = request.stage
    config = load_config(None)
    if not config.runtime.local_only:
        raise HTTPException(status_code=503, detail="local_only must remain enabled")
    store = FilesystemStore(config.storage.root)
    scene = _scene(store, project_id, scene_id)
    removed = invalidate_scene_dependencies(store, project_id, scene.index, requested_stage)
    scene = clear_scene_stage_outputs(scene, requested_stage)
    _persist_scene(store, project_id, scene)

    regenerated: list[str] = []
    attempts = 0
    strategies: list[str] = []
    try:
        if requested_stage == "image":
            image_provider = DiffusersImageProvider(
                config.image.model_path, device=config.image.device
            )
            image_result = generate_scene_image_with_recovery(
                image_provider,
                store,
                project_id,
                scene,
                model=config.image.model_path.name,
                width=config.image.width,
                height=config.image.height,
                steps=config.image.steps,
                guidance_scale=config.image.guidance_scale,
            )
            scene = image_result.scene.model_copy(
                update={
                    "metadata": {
                        **image_result.scene.metadata,
                        "image_recovery": {
                            "attempts": image_result.attempts,
                            "strategies": list(image_result.strategies),
                        },
                    }
                }
            )
            _persist_scene(store, project_id, scene)
            regenerated.append("image")
            attempts = image_result.attempts
            strategies.extend(image_result.strategies)
            scene = clear_scene_stage_outputs(scene, "video")
            _persist_scene(store, project_id, scene)

            video_provider = build_video_provider(config)
            video_result = generate_scene_video_with_recovery(
                video_provider,
                store,
                project_id,
                scene,
                width=config.video.width,
                height=config.video.height,
                fps=config.video.fps,
            )
            scene = video_result.scene.model_copy(
                update={
                    "metadata": {
                        **video_result.scene.metadata,
                        "video_recovery": {
                            "attempts": video_result.attempts,
                            "strategies": list(video_result.strategies),
                        },
                    }
                }
            )
            regenerated.append("video")
            attempts = max(attempts, video_result.attempts)
            strategies.extend(video_result.strategies)
        elif requested_stage == "audio":
            audio_provider = MacOSTTSProvider(sample_rate=config.tts.sample_rate)
            _, scene = generate_scene_audio(
                audio_provider,
                store,
                project_id,
                scene,
                voice=config.tts.voice,
                rate=config.tts.rate,
            )
            regenerated.append("audio")
            attempts = 1
            strategies = ["original"]
        else:
            video_provider = build_video_provider(config)
            video_result = generate_scene_video_with_recovery(
                video_provider,
                store,
                project_id,
                scene,
                width=config.video.width,
                height=config.video.height,
                fps=config.video.fps,
            )
            scene = video_result.scene.model_copy(
                update={
                    "metadata": {
                        **video_result.scene.metadata,
                        "video_recovery": {
                            "attempts": video_result.attempts,
                            "strategies": list(video_result.strategies),
                        },
                    }
                }
            )
            regenerated.append("video")
            attempts = video_result.attempts
            strategies = list(video_result.strategies)

        _persist_scene(store, project_id, scene)
        _finalize_project_media(store, project_id)
    except Exception as exc:
        _persist_scene(store, project_id, scene)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "scene": scene.model_dump(mode="json"),
        "requested_stage": requested_stage,
        "regenerated_stages": regenerated,
        "removed_artifacts": removed,
        "attempts": attempts,
        "strategies": strategies,
        "finalized": True,
    }


@router.post("/api/projects", status_code=202)
def create_project_async(request: CreateProjectRequest) -> dict[str, Any]:
    """Create project metadata immediately and plan it in the local worker."""
    config = load_config(None)
    if not config.runtime.local_only:
        raise HTTPException(status_code=503, detail="local_only must remain enabled")
    if config.llm.provider != "ollama":
        raise HTTPException(status_code=503, detail="local Ollama provider is required")

    project = VideoProject(
        source_prompt=request.prompt,
        duration_seconds=request.duration,
        aspect_ratio=request.aspect_ratio,
        style=request.style,
        quality_profile=config.runtime.profile,
    )
    store = FilesystemStore(config.storage.root)
    directory = store.create_project(project)
    job = _planning_manager().submit(project.id)
    return {
        "project_id": str(project.id),
        "path": str(directory),
        "job_id": str(job.id),
        "status": project.status.value,
    }


@router.get("/api/projects/{project_id}/planning-job")
def planning_job(project_id: UUID) -> dict[str, Any]:
    store = _store()
    jobs = _planning_manager().list(project_id)
    if not jobs:
        raise HTTPException(status_code=404, detail="planning job not found")
    return _planning_job_response(store, jobs[0])


@router.get("/api/planning-jobs/{job_id}")
def get_planning_job(job_id: UUID) -> dict[str, Any]:
    manager = _planning_manager()
    try:
        job = manager.get(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="planning job not found") from None
    return _planning_job_response(manager.store, job)
