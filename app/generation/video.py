"""Generate and persist one motion-video artifact for an individual scene."""

import hashlib
import json
from pathlib import Path
from uuid import UUID

from app.exceptions import VideoAgentError
from app.generation.cache import cache_key
from app.generation.video_qa import validate_scene_video
from app.models.artifact import Artifact
from app.models.scene import Scene
from app.providers.video import VideoGenerationRequest, VideoProvider
from app.storage.filesystem import FilesystemStore


def _load_cached_video(manifest_path: Path, expected_key: str) -> Artifact | None:
    """Return a valid cached video artifact when its generation key still matches."""
    if not manifest_path.is_file():
        return None
    try:
        artifact = Artifact.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if artifact.parameters.get("cache_key") != expected_key or not artifact.path.is_file():
        return None
    try:
        digest = hashlib.sha256(artifact.path.read_bytes()).hexdigest()
    except OSError:
        return None
    if artifact.sha256 != digest:
        return None
    return artifact


def generate_scene_video(
    provider: VideoProvider,
    store: FilesystemStore,
    project_id: UUID,
    scene: Scene,
    *,
    width: int = 704,
    height: int = 384,
    fps: int = 16,
    seed: int | None = None,
) -> tuple[Artifact, Scene]:
    """Generate a scene video and accept it only after deterministic QA."""
    directory = store.project_dir(project_id)
    if not directory.is_dir():
        raise ValueError(f"project does not exist: {project_id}")
    if scene.image_asset is None:
        raise VideoAgentError("scene has no image asset; generate the scene image first")
    if width <= 0 or height <= 0:
        raise ValueError("video dimensions must be positive")

    image_manifest = directory / f"scene-{scene.index:04d}-image.json"
    if not image_manifest.is_file():
        raise VideoAgentError(f"scene image manifest not found: {image_manifest}")
    try:
        image_data = json.loads(image_manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VideoAgentError("scene image manifest is invalid") from exc
    image_path_value = image_data.get("path")
    if not isinstance(image_path_value, str):
        raise VideoAgentError("scene image manifest has no valid path")
    image_path = Path(image_path_value)
    if not image_path.is_absolute():
        image_path = (directory / image_path).resolve()
    if directory.resolve() not in image_path.parents:
        raise VideoAgentError("scene image path escapes project directory")

    image_sha256 = image_data.get("sha256")
    if not isinstance(image_sha256, str) or not image_sha256:
        try:
            image_sha256 = hashlib.sha256(image_path.read_bytes()).hexdigest()
        except OSError as exc:
            raise VideoAgentError("scene image cannot be read") from exc

    provider_name = getattr(provider, "provider_name", provider.__class__.__name__)
    model_name = getattr(provider, "model_name", getattr(provider, "_model_name", "unknown"))
    generation_key = cache_key(
        "scene-video-v1",
        {
            "image_sha256": image_sha256,
            "provider": provider_name,
            "model": model_name,
            "prompt": scene.motion_prompt,
            "negative_prompt": scene.negative_prompt,
            "duration_seconds": scene.duration_seconds,
            "fps": fps,
            "width": width,
            "height": height,
            "seed": seed,
        },
    )

    video_manifest = directory / f"scene-{scene.index:04d}-video.json"
    cached = _load_cached_video(video_manifest, generation_key)
    if cached is not None:
        updated_scene = scene.model_copy(update={"video_asset": cached.id, "status": "ready"})
        store.write_json(directory, f"scene-{scene.index:04d}.json", updated_scene.model_dump(mode="json"))
        return cached, updated_scene

    videos_dir = directory / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    output = videos_dir / f"scene-{scene.index:04d}.mp4"
    result = provider.generate(
        VideoGenerationRequest(
            image_path=image_path,
            output_path=output,
            prompt=scene.motion_prompt,
            negative_prompt=scene.negative_prompt,
            duration_seconds=scene.duration_seconds,
            fps=fps,
            seed=seed,
            metadata={"scene_id": str(scene.id), "scene_index": scene.index, "width": width, "height": height},
        )
    )
    if not result.path.is_file() or result.path.stat().st_size == 0:
        raise VideoAgentError("video provider returned no usable video file")
    actual_sha256 = hashlib.sha256(result.path.read_bytes()).hexdigest()
    if actual_sha256 != result.sha256:
        raise VideoAgentError("video provider returned an invalid output hash")
    if result.duration_seconds <= 0 or result.fps <= 0:
        raise VideoAgentError("video provider returned invalid video metadata")

    qa = validate_scene_video(
        result.path,
        expected_duration=result.duration_seconds,
        expected_fps=result.fps,
        expected_resolution=(result.width, result.height),
    )
    artifact = Artifact(
        project_id=project_id,
        scene_id=scene.id,
        type="scene_video",
        path=result.path,
        mime="video/mp4",
        provider=result.provider,
        model=result.model,
        sha256=actual_sha256,
        parameters={
            "duration_seconds": qa["duration_seconds"],
            "fps": result.fps,
            "width": result.width,
            "height": result.height,
            "seed": seed,
            "prompt": scene.motion_prompt,
            "negative_prompt": scene.negative_prompt,
            "cache_key": generation_key,
            "qa": qa,
            **result.metadata,
        },
    )
    store.write_json(directory, f"scene-{scene.index:04d}-video.json", artifact.model_dump(mode="json"))
    updated_scene = scene.model_copy(update={"video_asset": artifact.id, "status": "ready"})
    store.write_json(directory, f"scene-{scene.index:04d}.json", updated_scene.model_dump(mode="json"))
    return artifact, updated_scene
