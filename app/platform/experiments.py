"""Reproducible local experiment manifests and result records."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ExperimentManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=200)
    provider: str = Field(min_length=1, max_length=200)
    provider_version: str = Field(min_length=1, max_length=50)
    parameters: dict[str, object] = Field(default_factory=dict)
    seed: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExperimentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment_id: UUID
    status: str = Field(pattern="^(planned|completed|failed)$")
    measurements: dict[str, float] = Field(default_factory=dict)
    notes: str = ""
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def write_experiment(root: Path, manifest: ExperimentManifest, result: ExperimentResult | None = None) -> Path:
    directory = (root.expanduser().resolve() / "experiments").resolve()
    directory.mkdir(parents=True, exist_ok=True)
    path = (directory / f"{manifest.id}.json").resolve()
    if directory not in path.parents:
        raise ValueError("experiment path escapes storage root")
    payload = {"manifest": manifest.model_dump(mode="json"), "result": result.model_dump(mode="json") if result else None}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def read_experiment(root: Path, experiment_id: UUID) -> dict[str, object]:
    path = root.expanduser().resolve() / "experiments" / f"{experiment_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))
