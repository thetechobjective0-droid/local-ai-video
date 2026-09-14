"""Local-only HTTP API for the video generation application."""

from uuid import UUID

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from app.config import load_config
from app.director.project import create_plan, resume_plan
from app.generation.video_recovery import generate_scene_video_with_recovery
from app.models.scene import Scene
from app.providers.factory import build_video_provider
from app.providers.ollama import OllamaProvider
from app.qa.project import validate_project
from app.qa.report import write_qa_report
from app.storage.filesystem import FilesystemStore
from app.web_ui import HTML

app = FastAPI(title="Local AI Video", version="0.1.0")


class CreateProjectRequest(BaseModel):
    model_config = {"extra": "forbid"}
    prompt: str = Field(min_length=1)
    duration: float = Field(default=60.0, gt=0)
    style: str = Field(default="cinematic", min_length=1)
    aspect_ratio: str = Field(default="16:9", min_length=3, max_length=16)


def _store() -> FilesystemStore:
    return FilesystemStore(load_config(None).storage.root)


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


def _local_config():
    config = load_config(None)
    if not config.runtime.local_only:
        raise HTTPException(status_code=503, detail="local_only must remain enabled")
    return config


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """Serve the local dashboard."""
    return HTML


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "local-only"}


@app.get("/api/projects")
def projects() -> list[dict[str, object]]:
    store = _store()
    root = store.root / "projects"
    result: list[dict[str, object]] = []
    for path in sorted(root.iterdir() if root.exists() else []):
        project_file = path / "project.json"
        if not path.is_dir() or not project_file.is_file():
            continue
        try:
            project = store.load_project(path.name)
        except (OSError, ValueError):
            continue
        result.append(project.model_dump(mode="json"))
    return result


@app.post("/api/projects", status_code=201)
def create_project(request: CreateProjectRequest) -> dict[str, object]:
    config = _local_config()
    if config.llm.provider != "ollama":
        raise HTTPException(status_code=503, detail="local Ollama provider is required")
    provider = OllamaProvider(config.llm.base_url)
    provider.require_health()
    provider.require_model(config.llm.model)
    store = FilesystemStore(config.storage.root)
    directory = create_plan(
        provider, store, request.prompt, request.duration, request.style, request.aspect_ratio,
        model=config.llm.model, temperature=config.llm.temperature, top_p=config.llm.top_p,
        top_k=config.llm.top_k, quality_profile=config.runtime.profile,
    )
    return {"project_id": directory.name, "path": str(directory)}


@app.get("/api/projects/{project_id}")
def project(project_id: UUID) -> dict[str, object]:
    store = _store()
    try:
        value = store.load_project(project_id)
    except (OSError, ValueError):
        raise HTTPException(status_code=404, detail="project not found") from None
    directory = store.project_dir(project_id)
    scenes = []
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
        raise HTTPException(status_code=503, detail="local Ollama provider is required")
    provider = OllamaProvider(config.llm.base_url)
    provider.require_health()
    provider.require_model(config.llm.model)
    store = FilesystemStore(config.storage.root)
    directory = resume_plan(provider, store, project_id, model=config.llm.model,
                            temperature=config.llm.temperature, top_p=config.llm.top_p,
                            top_k=config.llm.top_k)
    return {"project_id": directory.name, "path": str(directory)}


@app.get("/api/projects/{project_id}/qa")
def qa(project_id: UUID) -> dict[str, object]:
    store = _store()
    try:
        report = validate_project(store, project_id)
    except (OSError, ValueError):
        raise HTTPException(status_code=404, detail="project not found") from None
    write_qa_report(store.project_dir(project_id) / "qa-report.json", report)
    return report.model_dump(mode="json")


@app.post("/api/projects/{project_id}/scenes/{scene_id}/regenerate-video")
def regenerate_video(project_id: UUID, scene_id: UUID) -> dict[str, object]:
    config = _local_config()
    store = FilesystemStore(config.storage.root)
    scene = _scene(store, project_id, scene_id)
    provider = build_video_provider(config)
    result = generate_scene_video_with_recovery(
        provider, store, project_id, scene, width=config.video.width,
        height=config.video.height, fps=config.video.fps,
    )
    report = validate_project(store, project_id)
    write_qa_report(store.project_dir(project_id) / "qa-report.json", report)
    return {
        "scene": result.scene.model_dump(mode="json"),
        "attempts": result.attempts,
        "strategies": list(result.strategies),
        "qa_passed": report.passed,
    }


@app.get("/api/projects/{project_id}/video")
def final_video(project_id: UUID) -> FileResponse:
    path = _store().project_dir(project_id) / "final.mp4"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="final video not found")
    return FileResponse(path, media_type="video/mp4", filename="final.mp4")


def run() -> None:
    """Run the API on loopback only."""
    uvicorn.run(app, host="127.0.0.1", port=8765)
