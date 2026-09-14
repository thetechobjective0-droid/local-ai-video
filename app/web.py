"""Local-only HTTP API for the video generation application."""

import json
from pathlib import Path
from uuid import UUID

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from app.config import load_config
from app.director.project import create_plan, resume_plan
from app.generation.audio import generate_scene_audio
from app.generation.image_recovery import generate_scene_image_with_recovery
from app.generation.video_recovery import generate_scene_video_with_recovery
from app.models.scene import Scene
from app.providers.factory import build_video_provider
from app.providers.diffusers_image import DiffusersImageProvider
from app.providers.macos_tts import MacOSTTSProvider
from app.providers.ollama import OllamaProvider
from app.qa.project import validate_project
from app.qa.report import write_qa_report
from app.storage.filesystem import FilesystemStore
from app.web_ui import HTML
from app.job_api import router as job_router

app = FastAPI(title="Local AI Video", version="0.1.0")
app.include_router(job_router)


class CreateProjectRequest(BaseModel):
    model_config = {"extra": "forbid"}
    prompt: str = Field(min_length=1)
    duration: float = Field(default=60.0, gt=0)
    style: str = Field(default="cinematic", min_length=1)
    aspect_ratio: str = Field(default="16:9", min_length=3, max_length=16)


class RegenerateRequest(BaseModel):
    model_config = {"extra": "forbid"}
    stage: str = Field(default="video", pattern="^(image|audio|video)$")


def _store() -> FilesystemStore:
    return FilesystemStore(load_config(None).storage.root)


def _local_config():
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
    store.write_json(store.project_dir(project_id), f"scene-{scene.index:04d}.json", scene.model_dump(mode="json"))


def _artifact_path(store: FilesystemStore, project_id: UUID, scene_id: UUID, suffix: str) -> tuple[Path, str]:
    scene = _scene(store, project_id, scene_id)
    manifest = store.project_dir(project_id) / f"scene-{scene.index:04d}-{suffix}.json"
    if not manifest.is_file():
        raise HTTPException(status_code=404, detail=f"scene {suffix} artifact not found")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        artifact_id = UUID(str(data["id"]))
        path_value = Path(str(data["path"]))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=422, detail="artifact manifest is invalid") from None
    project_dir = store.project_dir(project_id).resolve()
    path = (path_value if path_value.is_absolute() else project_dir / path_value).resolve()
    if project_dir not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="artifact file not found")
    return path, str(artifact_id)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
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
    directory = create_plan(provider, store, request.prompt, request.duration, request.style, request.aspect_ratio,
                            model=config.llm.model, temperature=config.llm.temperature, top_p=config.llm.top_p,
                            top_k=config.llm.top_k, quality_profile=config.runtime.profile)
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
        raise HTTPException(status_code=503, detail="local Ollama provider required")
    provider = OllamaProvider(config.llm.base_url)
    provider.require_health()
    provider.require_model(config.llm.model)
    store = FilesystemStore(config.storage.root)
    directory = resume_plan(provider, store, project_id, model=config.llm.model, temperature=config.llm.temperature,
                            top_p=config.llm.top_p, top_k=config.llm.top_k)
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


@app.get("/api/projects/{project_id}/timeline")
def timeline(project_id: UUID) -> dict[str, object]:
    store = _store()
    path = store.project_dir(project_id) / "timeline.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="timeline not found")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=422, detail="timeline is invalid") from None


@app.get("/api/projects/{project_id}/subtitles/{format}")
def subtitles(project_id: UUID, format: str) -> FileResponse:
    if format not in {"srt", "vtt"}:
        raise HTTPException(status_code=404, detail="unsupported subtitle format")
    path = _store().project_dir(project_id) / f"subtitles.{format}"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="subtitle file not found")
    media_type = "text/vtt" if format == "vtt" else "application/x-subrip"
    return FileResponse(path, media_type=media_type, filename=path.name)


@app.get("/api/projects/{project_id}/scenes/{scene_id}/image")
def scene_image(project_id: UUID, scene_id: UUID) -> FileResponse:
    path, _ = _artifact_path(_store(), project_id, scene_id, "image")
    return FileResponse(path, media_type="image/png")


@app.get("/api/projects/{project_id}/scenes/{scene_id}/audio")
def scene_audio(project_id: UUID, scene_id: UUID) -> FileResponse:
    path, _ = _artifact_path(_store(), project_id, scene_id, "audio")
    return FileResponse(path, media_type="audio/wav")


@app.get("/api/projects/{project_id}/scenes/{scene_id}/video")
def scene_video(project_id: UUID, scene_id: UUID) -> FileResponse:
    path, _ = _artifact_path(_store(), project_id, scene_id, "video")
    return FileResponse(path, media_type="video/mp4")


@app.get("/api/projects/{project_id}/scenes/{scene_id}/artifacts")
def scene_artifacts(project_id: UUID, scene_id: UUID) -> dict[str, object]:
    store = _store()
    scene = _scene(store, project_id, scene_id)
    result: dict[str, object] = {"scene_id": str(scene.id), "artifacts": {}}
    for suffix in ("image", "audio", "video"):
        manifest = store.project_dir(project_id) / f"scene-{scene.index:04d}-{suffix}.json"
        if not manifest.is_file():
            continue
        try:
            artifact = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        result["artifacts"][suffix] = {**artifact, "url": f"/api/projects/{project_id}/scenes/{scene_id}/{suffix}"}
    return result


@app.post("/api/projects/{project_id}/scenes/{scene_id}/regenerate")
def regenerate(project_id: UUID, scene_id: UUID, request: RegenerateRequest) -> dict[str, object]:
    config = _local_config()
    store = FilesystemStore(config.storage.root)
    scene = _scene(store, project_id, scene_id)
    if request.stage == "image":
        provider = DiffusersImageProvider(config.image.model_path, device=config.image.device)
        result = generate_scene_image_with_recovery(provider, store, project_id, scene,
                                                     model=config.image.model_path.name,
                                                     width=config.image.width, height=config.image.height,
                                                     steps=config.image.steps, guidance_scale=config.image.guidance_scale)
        scene = result.scene.model_copy(update={"metadata": {**result.scene.metadata,
            "image_recovery": {"attempts": result.attempts, "strategies": list(result.strategies)}}})
        _persist_scene(store, project_id, scene)
        attempts, strategies = result.attempts, list(result.strategies)
    elif request.stage == "audio":
        provider = MacOSTTSProvider(sample_rate=config.tts.sample_rate)
        _, updated_scene = generate_scene_audio(provider, store, project_id, scene, voice=config.tts.voice, rate=config.tts.rate)
        scene = updated_scene
        attempts, strategies = 1, ["original"]
    else:
        provider = build_video_provider(config)
        result = generate_scene_video_with_recovery(provider, store, project_id, scene,
                                                     width=config.video.width, height=config.video.height,
                                                     fps=config.video.fps)
        scene = result.scene.model_copy(update={"metadata": {**result.scene.metadata,
            "video_recovery": {"attempts": result.attempts, "strategies": list(result.strategies)}}})
        _persist_scene(store, project_id, scene)
        attempts, strategies = result.attempts, list(result.strategies)
    report = validate_project(store, project_id)
    write_qa_report(store.project_dir(project_id) / "qa-report.json", report)
    return {"scene": scene.model_dump(mode="json"), "attempts": attempts,
            "strategies": strategies, "qa_passed": report.passed}


@app.get("/api/projects/{project_id}/video")
def final_video(project_id: UUID) -> FileResponse:
    path = _store().project_dir(project_id) / "final.mp4"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="final video not found")
    return FileResponse(path, media_type="video/mp4", filename="final.mp4")


def run() -> None:
    uvicorn.run(app, host="127.0.0.1", port=8765)
