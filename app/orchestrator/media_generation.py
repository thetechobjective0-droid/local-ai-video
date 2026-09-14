"""Project-level deterministic media generation orchestration."""

from dataclasses import dataclass
from uuid import UUID

from app.exceptions import VideoAgentError
from app.generation.video import generate_scene_video
from app.models.scene import MediaType, Scene
from app.orchestrator.media_strategy import VideoCapability, select_media_type
from app.providers.video import VideoProvider
from app.storage.filesystem import FilesystemStore


@dataclass(frozen=True)
class SceneMediaResult:
    """Resolved media strategy and resulting scene state."""

    scene: Scene
    selected_media_type: MediaType
    used_fallback: bool


def generate_project_media(
    store: FilesystemStore,
    project_id: UUID,
    scenes: list[Scene],
    *,
    video_provider: VideoProvider,
    video_capability: VideoCapability,
    fallback_provider: VideoProvider | None = None,
    available_memory_gb: float | None = None,
    width: int = 704,
    height: int = 384,
    fps: int = 16,
) -> list[SceneMediaResult]:
    """Resolve and generate media for every scene using bounded fallback logic."""
    if not scenes:
        raise VideoAgentError("cannot generate project media without scenes")

    results: list[SceneMediaResult] = []
    for scene in sorted(scenes, key=lambda item: item.index):
        selected = select_media_type(
            scene,
            video=video_capability,
            available_memory_gb=available_memory_gb,
        )
        current = scene
        used_fallback = False

        if selected is MediaType.IMAGE_TO_VIDEO:
            try:
                _, current = generate_scene_video(
                    video_provider,
                    store,
                    project_id,
                    current,
                    width=width,
                    height=height,
                    fps=fps,
                )
            except (VideoAgentError, ValueError):
                if fallback_provider is None:
                    raise
                _, current = generate_scene_video(
                    fallback_provider,
                    store,
                    project_id,
                    current,
                    width=width,
                    height=height,
                    fps=fps,
                )
                selected = MediaType.IMAGE_MOTION
                used_fallback = True
        elif selected is MediaType.IMAGE_MOTION:
            motion_provider = fallback_provider if fallback_provider is not None else video_provider
            _, current = generate_scene_video(
                motion_provider,
                store,
                project_id,
                current,
                width=width,
                height=height,
                fps=fps,
            )
        elif selected is MediaType.TEXT_TO_VIDEO:
            raise VideoAgentError("text-to-video routing is not implemented by the current project orchestrator")
        elif current.image_asset is None:
            raise VideoAgentError(f"scene {current.index} has no image asset for static media")

        current = current.model_copy(
            update={
                "metadata": {
                    **current.metadata,
                    "selected_media_type": selected.value,
                    "media_fallback_used": used_fallback,
                }
            }
        )
        directory = store.project_dir(project_id)
        store.write_json(directory, f"scene-{current.index:04d}.json", current.model_dump(mode="json"))
        results.append(SceneMediaResult(current, selected, used_fallback))

    return results
