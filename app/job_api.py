"""HTTP routes for local background jobs."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.orchestrator.jobs import get_job_manager
from app.orchestrator.planning_jobs import get_planning_job_manager
from app.storage.filesystem import FilesystemStore

router = APIRouter()


def _manager():
    from app.config import load_config

    return get_job_manager(FilesystemStore(load_config(None).storage.root))


def _planning_manager():
    from app.config import load_config

    return get_planning_job_manager(FilesystemStore(load_config(None).storage.root))


@router.post("/api/projects/{project_id}/jobs/media", status_code=202)
def create_media_job(project_id: UUID) -> dict[str, object]:
    manager = _manager()
    try:
        job = manager.submit(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="project not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return job.model_dump(mode="json")


@router.get("/api/jobs/{job_id}")
def get_media_job(job_id: UUID) -> dict[str, object]:
    try:
        return _manager().get(job_id).model_dump(mode="json")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found") from None


@router.get("/api/projects/{project_id}/jobs")
def list_media_jobs(project_id: UUID) -> list[dict[str, object]]:
    return [job.model_dump(mode="json") for job in _manager().list(project_id)]


@router.post("/api/projects", status_code=202)
def create_project_async(request: dict[str, object]) -> dict[str, object]:
    """Create project metadata immediately and plan it in the local worker."""
    from app.models.project import VideoProject

    config = __import__("app.config", fromlist=["load_config"]).load_config(None)
    if not config.runtime.local_only:
        raise HTTPException(status_code=503, detail="local_only must remain enabled")
    if config.llm.provider != "ollama":
        raise HTTPException(status_code=503, detail="local Ollama provider is required")

    try:
        project = VideoProject(
            source_prompt=str(request["prompt"]),
            duration_seconds=float(request.get("duration", 60.0)),
            aspect_ratio=str(request.get("aspect_ratio", "16:9")),
            style=str(request.get("style", "cinematic")),
            quality_profile=config.runtime.profile,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

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
def planning_job(project_id: UUID) -> dict[str, object]:
    jobs = _planning_manager().list(project_id)
    if not jobs:
        raise HTTPException(status_code=404, detail="planning job not found")
    return jobs[0].model_dump(mode="json")


@router.get("/api/planning-jobs/{job_id}")
def get_planning_job(job_id: UUID) -> dict[str, object]:
    try:
        return _planning_manager().get(job_id).model_dump(mode="json")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="planning job not found") from None
