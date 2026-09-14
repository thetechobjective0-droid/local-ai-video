"""Generate and persist one narration artifact for an individual scene."""

import hashlib
from uuid import UUID

from app.exceptions import VideoAgentError
from app.models.artifact import Artifact
from app.models.scene import Scene
from app.providers.tts import TTSProvider, TTSRequest
from app.storage.filesystem import FilesystemStore


def generate_scene_audio(
    provider: TTSProvider,
    store: FilesystemStore,
    project_id: UUID,
    scene: Scene,
    *,
    voice: str | None = None,
    rate: int = 180,
) -> tuple[Artifact, Scene]:
    """Synthesize scene narration and persist its metadata atomically."""
    if not scene.narration.strip():
        raise ValueError(f"scene {scene.id} has no narration")
    directory = store.project_dir(project_id)
    if not directory.is_dir():
        raise ValueError(f"project does not exist: {project_id}")

    audio_dir = directory / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    output = audio_dir / f"scene-{scene.index:04d}.wav"
    result = provider.synthesize(
        TTSRequest(
            text=scene.narration,
            output_path=output,
            voice=voice,
            rate=rate,
            metadata={"scene_id": str(scene.id), "scene_index": scene.index},
        )
    )
    if not result.path.is_file() or result.path.stat().st_size == 0:
        raise VideoAgentError("TTS provider returned no usable audio file")
    actual_sha256 = hashlib.sha256(result.path.read_bytes()).hexdigest()
    if actual_sha256 != result.sha256:
        raise VideoAgentError("TTS provider returned an invalid output hash")
    if result.duration_seconds <= 0:
        raise VideoAgentError("TTS provider returned non-positive duration")

    artifact = Artifact(
        project_id=project_id,
        scene_id=scene.id,
        type="scene_audio",
        path=result.path,
        mime="audio/wav",
        provider=result.provider,
        model=result.model,
        sha256=actual_sha256,
        parameters={
            "duration_seconds": result.duration_seconds,
            "sample_rate": result.sample_rate,
            "channels": result.channels,
            "voice": result.voice,
            "rate": rate,
            **result.metadata,
        },
    )
    store.write_json(
        directory,
        f"scene-{scene.index:04d}-audio.json",
        artifact.model_dump(mode="json"),
    )
    updated_scene = scene.model_copy(update={"audio_asset": artifact.id})
    store.write_json(
        directory,
        f"scene-{scene.index:04d}.json",
        updated_scene.model_dump(mode="json"),
    )
    return artifact, updated_scene
