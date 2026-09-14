"""Local-only HTTP API for the video generation application."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import UUID
import logging

import uvicorn
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from app.config import AppConfig, load_config
from app.director.project import resume_plan
from app.exceptions import ProviderUnavailableError
from app.generation.audio import generate_scene_audio
from app.generation.image_recovery import generate_scene_image_with_recovery
from app.generation.video_recovery import generate_scene_video_with_recovery
from app.logging import configure_logging
from app.models.scene import Scene
from app.providers.diffusers_image import DiffusersImageProvider
from app.providers.factory import build_video_provider
from app.providers.macos_tts import MacOSTTSProvider
from app.providers.ollama import OllamaProvider
from app.qa.project import validate_project
from app.qa.report import write_qa_report
from app.storage.filesystem import FilesystemStore
from app.web_ui import HTML
from app.job_api import router as job_router

app = FastAPI(title="Local AI Video", version="0.1.0")
app.include_router(job_router)
logger = logging.getLogger(__name__)


@app.on_event("startup")
def startup() -> None:
    configure_logging()
    logger.info("[web] application startup complete")


def _store() -> FilesystemStore:
    return FilesystemStore(load_config(None).storage.root)


@app.get("/api/projects/{project_id}/qa")
def qa(project_id: UUID) -> dict[str, Any]:
    store = _store()
    try:
        report = validate_project(store, project_id)
    except (OSError, ValueError):
        raise HTTPException(status_code=404, detail="project not found") from None
    write_qa_report(store.project_dir(project_id) / "qa-report.json", report)
    logger.info("[web] QA project=%s passed=%s failures=%s", project_id, report.passed, len(report.failures))
    return asdict(report)
