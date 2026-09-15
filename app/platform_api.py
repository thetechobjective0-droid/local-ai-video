"""Local APIs for V3 provider discovery and benchmark/experiment records."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.config import load_config
from app.platform.benchmarks import collect_environment_report, list_benchmark_reports
from app.platform.experiments import ExperimentManifest, ExperimentResult, read_experiment, write_experiment
from app.platform.registry import compatible_video_providers, list_providers, provider
from app.providers.capabilities import get_provider_capabilities
from app.storage.filesystem import FilesystemStore

router = APIRouter()


class ExperimentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    provider: str = Field(min_length=1, max_length=200)
    provider_version: str = Field(default="1.0", min_length=1, max_length=50)
    parameters: dict[str, object] = Field(default_factory=dict)
    seed: int | None = None


def _store() -> FilesystemStore:
    return FilesystemStore(load_config(None).storage.root)


@router.get("/api/platform/providers")
def platform_providers() -> list[dict[str, object]]:
    return [value.__dict__ for value in list_providers()]


@router.get("/api/platform/providers/{name}")
def platform_provider(name: str) -> dict[str, object]:
    try:
        return provider(name).__dict__
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.get("/api/platform/video-compatibility/{provider_name}")
def video_compatibility(provider_name: str) -> list[dict[str, object]]:
    capability = get_provider_capabilities(provider_name).video
    return [value.__dict__ for value in compatible_video_providers(capability)]


@router.post("/api/platform/benchmarks/environment")
def benchmark_environment(project_id: UUID | None = None) -> dict[str, object]:
    return collect_environment_report(_store(), project_id).to_dict()


@router.get("/api/platform/benchmarks")
def benchmark_history() -> list[dict[str, object]]:
    return list_benchmark_reports(_store().root)


@router.post("/api/platform/experiments")
def create_experiment(request: ExperimentRequest) -> dict[str, object]:
    manifest = ExperimentManifest(
        name=request.name,
        provider=request.provider,
        provider_version=request.provider_version,
        parameters=request.parameters,
        seed=request.seed,
    )
    path = write_experiment(_store().root, manifest)
    return {"experiment": manifest.model_dump(mode="json"), "path": str(path)}


@router.put("/api/platform/experiments/{experiment_id}")
def complete_experiment(experiment_id: UUID, status: str = "completed", measurements: dict[str, float] | None = None, notes: str = "") -> dict[str, object]:
    if status not in {"planned", "completed", "failed"}:
        raise HTTPException(status_code=422, detail="invalid experiment status")
    store = _store()
    try:
        payload = read_experiment(store.root, experiment_id)
    except (OSError, ValueError, KeyError):
        raise HTTPException(status_code=404, detail="experiment not found") from None
    manifest = ExperimentManifest.model_validate(payload["manifest"])
    result = ExperimentResult(experiment_id=experiment_id, status=status, measurements=measurements or {}, notes=notes)
    path = write_experiment(store.root, manifest, result)
    return {"experiment_id": str(experiment_id), "result": result.model_dump(mode="json"), "path": str(path)}


@router.get("/api/platform/experiments/{experiment_id}")
def get_experiment(experiment_id: UUID) -> dict[str, Any]:
    try:
        return read_experiment(_store().root, experiment_id)
    except (OSError, ValueError, KeyError):
        raise HTTPException(status_code=404, detail="experiment not found") from None
