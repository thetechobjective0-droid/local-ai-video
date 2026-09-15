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


def _effective_motion_prompt(scene: Scene) -> str:
    """Turn a terse storyboard motion instruction into a model-friendly shot prompt."""
    prompt = scene.motion_prompt.strip()
    visual = scene.visual_description.strip()
    camera = scene.camera.strip()
    composition = scene.composition.strip()
    lighting = scene.lighting.strip()
    parts = [part for part in (prompt, visual, camera, composition, lighting) if part]
    base = ". ".join(parts)
    quality = (
        " Smooth cinematic motion, physically plausible movement, stable subject identity, "
        "stable composition, coherent background geometry, natural temporal consistency, "
        "subtle camera movement, realistic depth and lighting, no abrupt cuts within the shot."
    )
    return (base + quality).strip() if base else quality.strip()


def _persist_native_audio(
    store: FilesystemStore,
    project_id: UUID,
    scene: Scene,
    metadata: dict[str, object],
) -> Scene:
    """Persist provider-generated synchronized audio as the scene's audio artifact."""
    value = metadata.get("native_audio_path")
    if not isinstance(value, str) or not value:
        return scene
    directory = store.project_dir(project_id).resolve()
    audio_path = Path(value).expanduser()
    if not audio_path.is_absolute():
        audio_path = (directory / audio_path).resolve()
    else:
        audio_path = audio_path.resolve()
    if directory not in audio_path.parents or not audio_path.is_file() or audio_path.stat().st_size == 0:
        raise VideoAgentError("video provider reported native audio, but the audio artifact is missing")
    digest = hashlib.sha256(audio_path.read_bytes()).hexdigest()
    artifact = Artifact(
        project_id=project_id,
        scene_id=scene.id,
        type="scene_audio",
        path=audio_path,
        mime="audio/wav",
        provider=str(metadata.get("provider", "ltx2_mlx")),
        model=str(metadata.get("model", "LTX-2.3-22B-MLX")),
        sha256=digest,
        parameters={
            "generation_mode": "native_synchronized_audio",
            "video_generation_mode": "ai_i2v",
            "sample_rate": 48000,
            "channels": 2,
            "sha256": digest,
        },
    )
    store.write_json(directory, f"scene-{scene.index:04d}-audio.json", artifact.model_dump(mode="json"))
    return scene.model_copy(update={"audio_asset": artifact.id})


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
    inference_steps: int = 40,
    guidance_scale: float = 3.0,
    guidance_rescale: float = 0.0,
    image_cond_noise_scale: float = 0.025,
    decode_timestep: float = 0.05,
    decode_noise_scale: float | None = 0.025,
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
    effective_prompt = _effective_motion_prompt(scene)
    generation_key = cache_key(
        "scene-video-v4",
        {
            "image_sha256": image_sha256,
            "provider": provider_name,
            "model": model_name,
            "prompt": effective_prompt,
            "negative_prompt": scene.negative_prompt,
            "duration_seconds": scene.duration_seconds,
            "fps": fps,
            "width": width,
            "height": height,
            "seed": seed,
            "inference_steps": inference_steps,
            "guidance_scale": guidance_scale,
            "guidance_rescale": guidance_rescale,
            "image_cond_noise_scale": image_cond_noise_scale,
            "decode_timestep": decode_timestep,
            "decode_noise_scale": decode_noise_scale,
        },
    )

    video_manifest = directory / f"scene-{scene.index:04d}-video.json"
    cached = _load_cached_video(video_manifest, generation_key)
    if cached is not None:
        updated_scene = scene.model_copy(update={"video_asset": cached.id, "status": "ready"})
        updated_scene = _persist_native_audio(store, project_id, updated_scene, cached.parameters)
        store.write_json(directory, f"scene-{scene.index:04d}.json", updated_scene.model_dump(mode="json"))
        return cached, updated_scene

    videos_dir = directory / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    output = videos_dir / f"scene-{scene.index:04d}.mp4"
    result = provider.generate(
        VideoGenerationRequest(
            image_path=image_path,
            output_path=output,
            prompt=effective_prompt,
            negative_prompt=scene.negative_prompt,
            duration_seconds=scene.duration_seconds,
            fps=fps,
            seed=seed,
            metadata={
                "project_root": str(directory),
                "scene_id": str(scene.id),
                "scene_index": scene.index,
                "width": width,
                "height": height,
                "inference_steps": inference_steps,
                "guidance_scale": guidance_scale,
                "guidance_rescale": guidance_rescale,
                "image_cond_noise_scale": image_cond_noise_scale,
                "decode_timestep": decode_timestep,
                "decode_noise_scale": decode_noise_scale,
            },
        )
    )
    if not result.path.is_file() or result.path.stat().st_size == 0:
        raise VideoAgentError("video provider returned no usable video file")
    actual_sha256 = hashlib.sha256(result.path.read_bytes()).hexdigest()
    if actual_sha256 != result.sha256:
        raise VideoAgentError("video provider returned an invalid output hash")
    if result.duration_seconds <= 0 or result.fps <= 0:
        raise VideoAgentError("video provider returned invalid video metadata")

    generation_mode = result.metadata.get("generation_mode")
    if provider_name in {"ltx_video", "ltx2_mlx"} and generation_mode != "ai_i2v":
        raise VideoAgentError(
            "AI video provider did not return an artifact marked as real temporal image-to-video"
        )
    if provider_name == "ltx2_mlx" and result.metadata.get("temporal_generation") is not True:
        raise VideoAgentError("LTX-2 MLX output did not confirm temporal frame generation")
    if provider_name == "ffmpeg_ken_burns" and generation_mode != "image_motion":
        raise VideoAgentError(
            "FFmpeg provider did not identify its output as deterministic image motion"
        )

    qa = validate_scene_video(
        result.path,
        expected_duration=result.duration_seconds,
        expected_fps=result.fps,
        expected_resolution=(result.width, result.height),
    )
    metadata = {**result.metadata, "provider": result.provider, "model": result.model}
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
            "prompt": effective_prompt,
            "negative_prompt": scene.negative_prompt,
            "generation_mode": generation_mode,
            "cache_key": generation_key,
            "qa": qa,
            **metadata,
        },
    )
    store.write_json(directory, f"scene-{scene.index:04d}-video.json", artifact.model_dump(mode="json"))
    updated_scene = scene.model_copy(update={"video_asset": artifact.id, "status": "ready"})
    updated_scene = _persist_native_audio(store, project_id, updated_scene, artifact.parameters)
    store.write_json(directory, f"scene-{scene.index:04d}.json", updated_scene.model_dump(mode="json"))
    return artifact, updated_scene
