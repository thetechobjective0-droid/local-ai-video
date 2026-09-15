"""V2/V3 operator and editing APIs kept separate from the stable job router."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import load_config
from app.evaluation import evaluate_project, write_evaluation_report
from app.models.scene import Scene
from app.orchestrator.approvals import get_approval, set_approval
from app.orchestrator.events import JobEventLog
from app.orchestrator.jobs import MediaJobManager
from app.orchestrator.scheduled_jobs import get_scheduled_job_manager
from app.storage.filesystem import FilesystemStore

router = APIRouter()


class SceneEditRequest(BaseModel):
    model_config = {"extra": "forbid"}

    duration_seconds: float | None = Field(default=None, gt=0)
    narration: str | None = Field(default=None, max_length=20_000)
    visual_description: str | None = Field(default=None, max_length=20_000)
    image_prompt: str | None = Field(default=None, max_length=20_000)
    motion_prompt: str | None = Field(default=None, max_length=20_000)
    voice: str | None = Field(default=None, max_length=200)
    transition: str | None = Field(default=None, max_length=100)
    subtitle_style: str | None = Field(default=None, max_length=100)


class ApprovalRequest(BaseModel):
    model_config = {"extra": "forbid"}

    status: str = Field(pattern="^(pending|approved|rejected)$")
    note: str | None = Field(default=None, max_length=2_000)


def _store() -> FilesystemStore:
    return FilesystemStore(load_config(None).storage.root)


def _manager() -> MediaJobManager:
    return get_scheduled_job_manager(_store())


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


def _save_scene(store: FilesystemStore, project_id: UUID, scene: Scene) -> None:
    store.write_json(store.project_dir(project_id), f"scene-{scene.index:04d}.json", scene.model_dump(mode="json"))


def _invalidate_final_outputs(store: FilesystemStore, project_id: UUID) -> None:
    directory = store.project_dir(project_id)
    for name in ("timeline.json", "subtitles.srt", "subtitles.vtt", "final.mp4", "qa-report.json", "evaluation-report.json"):
        path = directory / name
        if path.is_file():
            path.unlink()


@router.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: UUID) -> dict[str, Any]:
    try:
        return _manager().cancel(job_id).model_dump(mode="json")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found") from None


@router.post("/api/projects/{project_id}/shutdown")
def shutdown_project_workers(project_id: UUID) -> dict[str, object]:
    jobs = [job for job in _manager().list(project_id) if job.state in {"queued", "running"}]
    for job in jobs:
        _manager().cancel(job.id)
    return {"cancelled_jobs": [str(job.id) for job in jobs]}


@router.patch("/api/projects/{project_id}/scenes/{scene_id}")
def edit_scene(project_id: UUID, scene_id: UUID, request: SceneEditRequest) -> dict[str, Any]:
    store = _store()
    scene = _scene(store, project_id, scene_id)
    updates = request.model_dump(exclude_none=True)
    metadata = dict(scene.metadata)
    for key in ("voice", "transition", "subtitle_style"):
        if key in updates:
            metadata[key] = updates.pop(key)
    edited = scene.model_copy(update={**updates, "metadata": metadata, "status": "pending"})
    _invalidate_final_outputs(store, project_id)
    _save_scene(store, project_id, edited)
    JobEventLog(store.root, project_id).append(
        "scene_edited", stage="editing", state="updated", details={"scene_id": str(scene_id), "fields": sorted(request.model_dump(exclude_none=True))}
    )
    return edited.model_dump(mode="json")


@router.post("/api/projects/{project_id}/scenes/reorder")
def reorder_scenes(project_id: UUID, scene_ids: list[UUID]) -> dict[str, object]:
    store = _store()
    scenes: list[Scene] = []
    for path in sorted(store.project_dir(project_id).glob("scene-*.json")):
        if path.name.endswith(("-image.json", "-audio.json", "-video.json")):
            continue
        try:
            scenes.append(Scene.model_validate_json(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    by_id = {scene.id: scene for scene in scenes}
    if len(scene_ids) != len(scenes) or set(scene_ids) != set(by_id):
        raise HTTPException(status_code=422, detail="scene_ids must contain every scene exactly once")
    cursor = 0.0
    ordered: list[Scene] = []
    for index, scene_id in enumerate(scene_ids, start=1):
        scene = by_id[scene_id].model_copy(update={"index": index, "start_seconds": cursor, "status": "pending"})
        ordered.append(scene)
        cursor += scene.duration_seconds
    project = store.load_project(project_id)
    if cursor > project.duration_seconds + 0.05:
        raise HTTPException(status_code=422, detail="reordered scenes exceed project duration")
    for path in store.project_dir(project_id).glob("scene-*.json"):
        if path.name.endswith(("-image.json", "-audio.json", "-video.json")):
            continue
        path.unlink()
    for scene in ordered:
        _save_scene(store, project_id, scene)
    _invalidate_final_outputs(store, project_id)
    JobEventLog(store.root, project_id).append("scene_reordered", stage="editing", state="updated", details={"scene_ids": [str(value) for value in scene_ids]})
    return {"scenes": [scene.model_dump(mode="json") for scene in ordered]}


@router.get("/api/projects/{project_id}/approvals/{stage}")
def approval_status(project_id: UUID, stage: str) -> dict[str, object]:
    record = get_approval(_store().root, project_id, stage)
    return record.model_dump(mode="json") if record else {"project_id": str(project_id), "stage": stage, "status": "pending"}


@router.put("/api/projects/{project_id}/approvals/{stage}")
def update_approval(project_id: UUID, stage: str, request: ApprovalRequest) -> dict[str, object]:
    store = _store()
    record = set_approval(store.root, project_id, stage, request.status, note=request.note)
    JobEventLog(store.root, project_id).append("approval_updated", stage=stage, state=request.status, details={"note": request.note})
    return record.model_dump(mode="json")


@router.get("/api/projects/{project_id}/evaluation")
def evaluate(project_id: UUID) -> dict[str, object]:
    store = _store()
    report = evaluate_project(store, project_id)
    path = write_evaluation_report(store, project_id, report)
    JobEventLog(store.root, project_id).append("evaluation_completed", stage="evaluation", state="completed", details={"path": str(path.name), "passed": report.passed})
    return report.to_dict()
