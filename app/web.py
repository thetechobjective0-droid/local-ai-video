"""Local-only HTTP API for the video generation application."""

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import UUID

import uvicorn
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from app.advanced_api import router as advanced_router
from app.config import AppConfig, load_config
from app.director.project import resume_plan
from app.exceptions import ProviderUnavailableError
from app.generation.audio import generate_scene_audio
from app.generation.image_recovery import generate_scene_image_with_recovery
from app.generation.video_recovery import generate_scene_video_with_recovery
from app.job_api import router as job_router
from app.logging import configure_logging
from app.models.artifact import Artifact
from app.models.scene import Scene
from app.providers.diffusers_image import DiffusersImageProvider
from app.providers.factory import build_video_provider
from app.providers.macos_tts import MacOSTTSProvider
from app.providers.ollama import OllamaProvider
from app.qa.project import validate_project
from app.qa.report import write_qa_report
from app.storage.filesystem import FilesystemStore
from app.web_ui import HTML

app = FastAPI(title="Local AI Video", version="0.1.0")
app.include_router(job_router)
app.include_router(advanced_router)
logger = logging.getLogger(__name__)


@app.on_event("startup")
def startup_logging() -> None:
    configure_logging()
    logger.info("[web] application startup complete")


class RegenerateRequest(BaseModel):
    model_config = {"extra": "forbid"}
    stage: str = Field(default="video", pattern="^(image|audio|video)$")


def _store() -> FilesystemStore:
    return FilesystemStore(load_config(None).storage.root)


def _local_config() -> AppConfig:
    config = load_config(None)
    if not config.runtime.local_only:
        raise HTTPException(status_code=503, detail="local_only must remain enabled")
    return config


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


def _artifact_manifest(
    store: FilesystemStore, project_id: UUID, scene_id: UUID, suffix: str
) -> tuple[Artifact, Path]:
    scene = _scene(store, project_id, scene_id)
    manifest = store.project_dir(project_id) / f"scene-{scene.index:04d}-{suffix}.json"
    if not manifest.is_file():
        raise HTTPException(status_code=404, detail=f"scene {suffix} artifact not found")
    try:
        artifact = Artifact.model_validate_json(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise HTTPException(status_code=422, detail="artifact manifest is invalid") from None
    if artifact.project_id != project_id:
        raise HTTPException(status_code=422, detail="artifact manifest belongs to another project")
    expected_type = {"image": "scene_image", "audio": "scene_audio", "video": "scene_video"}[suffix]
    if artifact.type != expected_type:
        raise HTTPException(status_code=422, detail="artifact manifest has an invalid type")
    try:
        path = store.project_path(project_id, artifact.path, must_exist=True)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="artifact file not found") from None
    return artifact, path


def _artifact_path(
    store: FilesystemStore, project_id: UUID, scene_id: UUID, suffix: str
) -> tuple[Path, str]:
    artifact, path = _artifact_manifest(store, project_id, scene_id, suffix)
    return path, str(artifact.id)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    logger.info("[web] GET /")
    return HTML


@app.get("/api/health")
def health() -> dict[str, str]:
    logger.info("[web] GET /api/health")
    return {"status": "ok", "mode": "local-only"}


@app.get("/api/projects")
def projects() -> list[dict[str, Any]]:
    store = _store()
    result: list[dict[str, Any]] = []
    for path in sorted((store.root / "projects").iterdir() if (store.root / "projects").exists() else []):
        project_file = path / "project.json"
        if not path.is_dir() or not project_file.is_file():
            continue
        try:
            project = store.load_project(path.name)
        except (OSError, ValueError):
            continue
        result.append(project.model_dump(mode="json"))
    return result


@app.get("/api/projects/{project_id}")
def project(project_id: UUID) -> dict[str, Any]:
    store = _store()
    try:
        value = store.load_project(project_id)
    except (OSError, ValueError):
        raise HTTPException(status_code=404, detail="project not found") from None
    directory = store.project_dir(project_id)
    scenes: list[dict[str, Any]] = []
    for path in sorted(directory.glob("scene-*.json")):
        if path.name.endswith(("-image.json", "-audio.json", "-video.json")):
            continue
        try:
            scenes.append(Scene.model_validate_json(path.read_text(encoding="utf-8")).model_dump(mode="json"))
        except (OSError, ValueError):
            continue
    return {"project": value.model_dump(mode="json"), "scenes": scenes}


@app.post("/api/projects/{project_id}/resume")
def resume(project_id: UUID) -> dict[str, str]:
    config = _local_config()
    if config.llm.provider != "ollama":
        raise HTTPException(status_code=503, detail="local Ollama provider required")
    provider = OllamaProvider(config.llm.base_url)
    provider.require_health()
    provider.require_model(config.llm.model)
    store = FilesystemStore(config.storage.root)
    directory = resume_plan(provider, store, str(project_id), model=config.llm.model, temperature=config.llm.temperature, top_p=config.llm.top_p, top_k=config.llm.top_k)
    return {"project_id": directory.name, "path": str(directory)}


@app.get("/api/projects/{project_id}/qa")
def qa(project_id: UUID) -> dict[str, Any]:
    store = _store()
    try:
        report = validate_project(store, project_id)
    except (OSError, ValueError):
        raise HTTPException(status_code=404, detail="project not found") from None
    write_qa_report(store.project_dir(project_id) / "qa-report.json", report)
    return asdict(report)


@app.get("/api/projects/{project_id}/timeline")
def timeline(project_id: UUID) -> dict[str, Any]:
    store = _store()
    path = store.project_dir(project_id) / "timeline.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="timeline not found")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/projects/{project_id}/video/status")
def video_status(project_id: UUID) -> dict[str, object]:
    path = _store().project_dir(project_id) / "final.mp4"
    ready = path.is_file() and path.stat().st_size > 0
    return {"ready": ready, "url": f"/api/projects/{project_id}/video" if ready else None}


@app.get("/api/projects/{project_id}/video")
def video(project_id: UUID) -> Response:
    path = _store().project_dir(project_id) / "final.mp4"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="final video not found")
    return FileResponse(path, media_type="video/mp4", filename="final.mp4")


def run() -> None:
    config = load_config(None)
    uvicorn.run(app, host=config.web.host, port=config.web.port, log_level="info")
