"""Selective scene regeneration and downstream artifact invalidation."""

from __future__ import annotations

from pathlib import Path
from typing import Literal
from uuid import UUID

from app.orchestrator.checkpoints import checkpoint_path
from app.storage.filesystem import FilesystemStore

RegenerationStage = Literal["image", "audio", "video"]

_STAGE_ARTIFACTS: dict[RegenerationStage, tuple[str, ...]] = {
    "image": ("image", "video"),
    "audio": ("audio",),
    "video": ("video",),
}


def _manifest_path(project_dir: Path, scene_index: int, stage: str) -> Path:
    return project_dir / f"scene-{scene_index:04d}-{stage}.json"


def _artifact_path_from_manifest(path: Path) -> Path | None:
    try:
        import json

        payload = json.loads(path.read_text(encoding="utf-8"))
        value = payload.get("path")
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(value, str):
        return None
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = (path.parent / candidate).resolve()
    root = path.parent.resolve()
    if root not in candidate.parents:
        return None
    return candidate


def invalidate_scene_dependencies(
    store: FilesystemStore,
    project_id: UUID,
    scene_index: int,
    stage: RegenerationStage,
    *,
    job_id: UUID | str | None = None,
) -> list[str]:
    """Delete stale downstream artifacts/checkpoints while preserving unrelated scenes."""
    project_dir = store.project_dir(project_id)
    removed: list[str] = []
    for dependency in _STAGE_ARTIFACTS[stage]:
        manifest = _manifest_path(project_dir, scene_index, dependency)
        artifact = _artifact_path_from_manifest(manifest) if manifest.is_file() else None
        for path in (manifest, artifact):
            if path is None or not path.exists():
                continue
            path.unlink()
            removed.append(str(path.relative_to(project_dir)))

    stale_outputs = (
        project_dir / "timeline.json",
        project_dir / "subtitles.srt",
        project_dir / "subtitles.vtt",
        project_dir / "final.mp4",
        project_dir / "qa-report.json",
        project_dir / "evaluation-report.json",
    )
    for path in stale_outputs:
        if path.is_file():
            path.unlink()
            removed.append(str(path.relative_to(project_dir)))

    if job_id is not None:
        checkpoints = project_dir / "checkpoints"
        for checkpoint_stage in ("media", "finalize"):
            path = checkpoint_path(store.root, project_id, str(job_id), checkpoint_stage)
            if path.is_file():
                path.unlink()
                removed.append(str(path.relative_to(project_dir)))

    return removed
