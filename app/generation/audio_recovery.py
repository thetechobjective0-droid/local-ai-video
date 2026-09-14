"""Deterministic narration duration correction using local FFmpeg."""

import hashlib
import subprocess
from pathlib import Path
from uuid import UUID

from app.exceptions import VideoAgentError
from app.models.artifact import Artifact
from app.models.scene import Scene
from app.storage.filesystem import FilesystemStore


AUDIO_DURATION_TOLERANCE_SECONDS = 0.25


def correct_scene_audio_duration(
    store: FilesystemStore,
    project_id: UUID,
    scene: Scene,
    *,
    ffmpeg_command: str = "ffmpeg",
    tolerance_seconds: float = AUDIO_DURATION_TOLERANCE_SECONDS,
) -> tuple[Artifact, Scene]:
    """Pad or trim scene narration to the canonical scene duration when needed."""
    if scene.audio_asset is None:
        raise VideoAgentError("scene has no audio asset to correct")
    if tolerance_seconds < 0:
        raise ValueError("audio duration tolerance must not be negative")

    directory = store.project_dir(project_id)
    manifest_path = directory / f"scene-{scene.index:04d}-audio.json"
    if not manifest_path.is_file():
        raise VideoAgentError(f"scene audio manifest not found: {manifest_path}")
    try:
        artifact = Artifact.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise VideoAgentError("scene audio manifest is invalid") from exc
    if artifact.id != scene.audio_asset:
        raise VideoAgentError("scene audio asset UUID does not match its manifest")

    source = artifact.path.expanduser()
    if not source.is_absolute():
        source = (directory / source).resolve()
    if directory.resolve() not in source.parents or not source.is_file():
        raise VideoAgentError("scene audio path is missing or escapes project directory")

    actual_duration = float(artifact.parameters.get("duration_seconds", 0.0))
    if actual_duration <= 0:
        raise VideoAgentError("scene audio manifest has no valid duration")
    if abs(actual_duration - scene.duration_seconds) <= tolerance_seconds:
        return artifact, scene

    output = source.with_name(f".{source.stem}.duration-corrected.wav")
    duration = f"{scene.duration_seconds:.6f}"
    command = [
        ffmpeg_command,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-af",
        f"apad,atrim=duration={duration},asetpts=N/SR/TB",
        "-c:a",
        "pcm_s16le",
        str(output),
    ]
    try:
        completed = subprocess.run(
            command, check=False, capture_output=True, text=True, timeout=120
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise VideoAgentError("FFmpeg narration duration correction is unavailable") from exc
    if completed.returncode != 0:
        raise VideoAgentError(f"narration duration correction failed: {completed.stderr.strip()}")
    if not output.is_file() or output.stat().st_size == 0:
        raise VideoAgentError("narration duration correction produced no usable audio")

    corrected_sha = hashlib.sha256(output.read_bytes()).hexdigest()
    source.unlink(missing_ok=True)
    output.replace(source)
    corrected = artifact.model_copy(
        update={
            "sha256": corrected_sha,
            "parameters": {
                **artifact.parameters,
                "duration_seconds": scene.duration_seconds,
                "duration_correction": {
                    "applied": True,
                    "original_duration_seconds": actual_duration,
                    "target_duration_seconds": scene.duration_seconds,
                    "method": "pad_or_trim",
                },
            },
        }
    )
    store.write_json(directory, manifest_path.name, corrected.model_dump(mode="json"))
    return corrected, scene
