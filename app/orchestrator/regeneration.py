"""Selective scene regeneration and downstream artifact invalidation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal
from uuid import UUID

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
) -> list[str]:
    """Delete stale scene/downstream outputs while preserving unrelated scenes."""
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

    checkpoints = project_dir / "checkpoints"
    if checkpoints.is_dir():
        for path in (*checkpoints.glob("*-media.json"), *checkpoints.glob("*-finalize.json")):
            path.unlink()
            removed.append(str(path.relative_to(project_dir)))

    return removed


def clear_scene_stage_outputs(scene, stage: RegenerationStage):
    """Clear Scene references that would otherwise point at invalidated artifacts."""
    updates: dict[str, object] = {"status": "pending"}
    if stage == "image":
        updates.update({"image_asset": None, "video_asset": None})
    elif stage == "audio":
        updates.update({"audio_asset": None})
    else:
        updates.update({"video_asset": None})
    return scene.model_copy(update=updates)
