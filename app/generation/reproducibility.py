"""Reproducibility metadata for V2 project generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from app.models.project import VideoProject


@dataclass(frozen=True)
class ReproducibilityManifest:
    """Immutable inputs captured for a generation/render operation."""

    manifest_version: str
    project_id: str
    created_at: str
    source_prompt: str
    seed: int | None
    provider: str
    model: str
    parameters: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_manifest(
    project: VideoProject,
    *,
    provider: str,
    model: str,
    parameters: dict[str, Any] | None = None,
    seed: int | None = None,
) -> ReproducibilityManifest:
    """Capture deterministic project inputs without embedding mutable machine state."""
    return ReproducibilityManifest(
        manifest_version="1.0",
        project_id=str(project.id),
        created_at=datetime.now(timezone.utc).isoformat(),
        source_prompt=project.source_prompt,
        seed=seed,
        provider=provider,
        model=model,
        parameters=dict(parameters or {}),
    )


def write_manifest(path: Path, manifest: ReproducibilityManifest) -> Path:
    """Atomically write a reproducibility manifest."""
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        {**manifest.to_dict(), "fingerprint": manifest.fingerprint()},
        indent=2,
        ensure_ascii=False,
    ) + "\n"
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)
    return path
