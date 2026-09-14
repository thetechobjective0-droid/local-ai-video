"""HTTP routes for asynchronous local project planning."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.config import load_config
from app.models.project import VideoProject
from app.orchestrator.planning_jobs import get_planning_job_manager
from app.storage.filesystem import FilesystemStore

router = APIRouter()


def _store() -> FilesystemStore:
    return FilesystemStore(load_config(None).storage.root)


@router.post("/api/projects", status_code=202)
def create_project_async(request) -> dict[str, object]:
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
    store = _store()
    directory = store.create_project(project)
    job = get_planning_job_manager(store).submit(project.id)
    return {
        "project_id": str(project.id),
        "path": str(directory),
        "job_id": str(job.id),
        "status": project.status.value,
    }


@router.get("/api/projects/{project_id}/planning-job")
def planning_job(project_id: UUID) -> dict[str, object]:
    try:
        store = _store()
        jobs = get_planning_job_manager(store).list(project_id)
        if not jobs:
            raise FileNotFoundError
        return jobs[0].model_dump(mode="json")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="planning job not found") from None


@router.get("/api/planning-jobs/{job_id}")
def get_planning_job(job_id: UUID) -> dict[str, object]:
    try:
        return get_planning_job_manager(_store()).get(job_id).model_dump(mode="json")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="planning job not found") from None
