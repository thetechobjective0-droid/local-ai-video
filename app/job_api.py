"""HTTP routes for local background jobs."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import load_config
from app.models.project import ProjectStatus, VideoProject
from app.orchestrator.jobs import MediaJobManager, get_job_manager
from app.orchestrator.planning_jobs import PlanningJobManager, get_planning_job_manager
from app.storage.filesystem import FilesystemStore

router = APIRouter()


class CreateProjectRequest(BaseModel):
    """Validated request for asynchronous project creation."""

    model_config = {"extra": "forbid"}

    prompt: str = Field(min_length=1)
    duration: float = Field(default=60.0, gt=0)
    style: str = Field(default="cinematic", min_length=1)
    aspect_ratio: str = Field(default="16:9", min_length=3, max_length=16)


def _store() -> FilesystemStore:
    return FilesystemStore(load_config(None).storage.root)


def _manager() -> MediaJobManager:
    return get_job_manager(_store())


def _planning_manager() -> PlanningJobManager:
    return get_planning_job_manager(_store())


def _planning_job_response(store: FilesystemStore, job: Any) -> dict[str, Any]:
    """Expose planning completion when the durable project is already storyboard-ready.

    A synchronous Resume can finish planning after an older background job has failed.
    The project status is the authoritative planning result, so the job API must not
    report a stale failed state over a successfully materialized storyboard.
    """
    project = store.load_project(job.project_id)
    if project.status == ProjectStatus.STORYBOARD_READY and job.state != "completed":
        job = job.model_copy(
            update={"state": "completed", "completed_stage": "storyboard", "error": None}
        )
    return job.model_dump(mode="json")


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
            status_code=409,
            detail={"code": "planning_not_ready", "message": str(exc)},
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
