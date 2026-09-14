"""HTTP routes for local background media jobs."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.orchestrator.jobs import get_job_manager
from app.storage.filesystem import FilesystemStore

router = APIRouter()


def _manager():
    from app.config import load_config

    return get_job_manager(FilesystemStore(load_config(None).storage.root))


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
