"""Project-level deterministic media generation orchestration."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from uuid import UUID

from app.exceptions import VideoAgentError
from app.generation.image_recovery import generate_scene_image_with_recovery
from app.generation.video import generate_scene_video
from app.generation.video_recovery import generate_scene_video_with_recovery
from app.models.project import ProjectStatus
from app.models.scene import MediaType, Scene
from app.orchestrator.fallback import resolve_video_fallback
from app.orchestrator.media_strategy import VideoCapability, select_media_type
from app.preflight import ResourceSnapshot, memory_gib, snapshot
from app.providers.capabilities import get_provider_capabilities
from app.providers.image import ImageProvider
from app.providers.video import VideoProvider
from app.storage.filesystem import FilesystemStore


@dataclass(frozen=True)
class SceneMediaResult:
    """Resolved media strategy and resulting scene state."""

    scene: Scene
    selected_media_type: MediaType
    used_fallback: bool


def _provider_capability(provider: VideoProvider) -> VideoCapability:
    """Resolve registry capabilities from a concrete provider instance."""
    provider_name = getattr(provider, "provider_name", None)
    if not isinstance(provider_name, str):
        raise VideoAgentError("video provider does not expose a registered provider_name")
    return get_provider_capabilities(provider_name).video


def _provider_identity(provider: VideoProvider) -> tuple[str, str]:
    """Return stable provider/model identifiers for audit metadata."""
    name = getattr(provider, "provider_name", None)
    model = getattr(provider, "model_name", getattr(provider, "_model_name", "unknown"))
    if not isinstance(name, str) or not name:
        raise VideoAgentError("video provider does not expose a provider_name")
    if not isinstance(model, str) or not model:
        model = "unknown"
    return name, model


def _resolve_resources(
    store: FilesystemStore, resource_snapshot: ResourceSnapshot | None
) -> ResourceSnapshot:
    """Use an explicit resource snapshot or capture one immediately before generation."""
    return resource_snapshot if resource_snapshot is not None else snapshot(store.root)


def _set_project_status(store: FilesystemStore, project_id: UUID, status: ProjectStatus) -> None:
    """Persist a project lifecycle transition with a fresh update timestamp."""
    project = store.load_project(project_id)
    updated = project.model_copy(
        update={"status": status, "updated_at": datetime.now(timezone.utc)}
    )
    store.write_json(store.project_dir(project_id), "project.json", updated.model_dump(mode="json"))


def generate_project_media(
    store: FilesystemStore,
    project_id: UUID,
    scenes: list[Scene],
    *,
    video_provider: VideoProvider,
    image_provider: ImageProvider | None = None,
    image_model: str | None = None,
    image_width: int = 1024,
    image_height: int = 576,
    image_steps: int = 30,
    image_guidance_scale: float = 7.0,
    image_seed: int | None = None,
    video_capability: VideoCapability | None = None,
    fallback_provider: VideoProvider | None = None,
    available_memory_gb: float | None = None,
    resource_snapshot: ResourceSnapshot | None = None,
    width: int = 704,
    height: int = 384,
    fps: int = 16,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[SceneMediaResult]:
    """Generate project media with bounded recovery and deterministic fallback."""
    if not scenes:
        raise VideoAgentError("cannot generate project media without scenes")

    resources = _resolve_resources(store, resource_snapshot)
    measured_memory_gb = memory_gib(resources.available_memory_bytes)
    effective_memory_gb = measured_memory_gb if available_memory_gb is None else available_memory_gb
    capability = video_capability or _provider_capability(video_provider)
    ordered_scenes = sorted(scenes, key=lambda item: item.index)
    _set_project_status(store, project_id, ProjectStatus.ASSETS_GENERATING)
    results: list[SceneMediaResult] = []
    try:
        for completed_count, scene in enumerate(ordered_scenes, start=1):
            current = scene
            if image_provider is not None and current.image_asset is None:
                image_kwargs: dict[str, object] = {
                    "width": image_width,
                    "height": image_height,
                    "steps": image_steps,
                    "guidance_scale": image_guidance_scale,
                    "seed": image_seed,
                }
                if image_model is not None:
                    image_kwargs["model"] = image_model
                image_result = generate_scene_image_with_recovery(
                    image_provider, store, project_id, current, **image_kwargs
                )
                current = image_result.scene.model_copy(
                    update={
                        "metadata": {
                            **image_result.scene.metadata,
                            "image_recovery": {
                                "attempts": image_result.attempts,
                                "strategies": list(image_result.strategies),
                            },
                        }
                    }
                )
                store.write_json(
                    store.project_dir(project_id),
                    f"scene-{current.index:04d}.json",
                    current.model_dump(mode="json"),
                )

            selected = select_media_type(
                current, video=capability, available_memory_gb=effective_memory_gb
            )
            used_fallback = False
            fallback_metadata: dict[str, object] | None = None

            if selected is MediaType.IMAGE_TO_VIDEO:
                try:
                    video_result = generate_scene_video_with_recovery(
                        video_provider,
                        store,
                        project_id,
                        current,
                        width=width,
                        height=height,
                        fps=fps,
                    )
                    current = video_result.scene.model_copy(
                        update={
                            "metadata": {
                                **video_result.scene.metadata,
                                "video_recovery": {
                                    "attempts": video_result.attempts,
                                    "strategies": list(video_result.strategies),
                                    "fallback_used": False,
                                },
                            }
                        }
                    )
                except VideoAgentError as primary_error:
                    decision = resolve_video_fallback(
                        video_provider,
                        fallback_provider,
                        reason=f"primary provider failed after {3} bounded attempts: {primary_error}",
                    )
                    if decision is None:
                        raise
                    fallback_name, fallback_model = _provider_identity(decision.provider)
                    _, current = generate_scene_video(
                        decision.provider,
                        store,
                        project_id,
                        current,
                        width=width,
                        height=height,
                        fps=fps,
                    )
                    selected = MediaType.IMAGE_MOTION
                    used_fallback = True
                    fallback_metadata = {
                        "fallback_used": True,
                        "primary_provider": decision.primary_provider,
                        "fallback_provider": fallback_name,
                        "fallback_model": fallback_model,
                        "reason": decision.reason,
                    }
            elif selected is MediaType.IMAGE_MOTION:
                motion_provider = (
                    fallback_provider if fallback_provider is not None else video_provider
                )
                video_result = generate_scene_video_with_recovery(
                    motion_provider, store, project_id, current, width=width, height=height, fps=fps
                )
                current = video_result.scene.model_copy(
                    update={
                        "metadata": {
                            **video_result.scene.metadata,
                            "video_recovery": {
                                "attempts": video_result.attempts,
                                "strategies": list(video_result.strategies),
                                "fallback_used": motion_provider is not video_provider,
                            },
                        }
                    }
                )
            elif selected is MediaType.TEXT_TO_VIDEO:
                raise VideoAgentError(
                    "text-to-video routing is not implemented by the current project orchestrator"
                )
            elif current.image_asset is None:
                raise VideoAgentError(f"scene {current.index} has no image asset for static media")

            metadata = {
                **current.metadata,
                "selected_media_type": selected.value,
                "media_fallback_used": used_fallback,
                "resource_snapshot": {
                    "total_memory_bytes": resources.total_memory_bytes,
                    "available_memory_bytes": resources.available_memory_bytes,
                    "free_disk_bytes": resources.free_disk_bytes,
                },
                "routing_memory_gib": effective_memory_gb,
            }
            if fallback_metadata is not None:
                metadata["media_fallback"] = fallback_metadata
            current = current.model_copy(update={"metadata": metadata})
            store.write_json(
                store.project_dir(project_id),
                f"scene-{current.index:04d}.json",
                current.model_dump(mode="json"),
            )
            results.append(SceneMediaResult(current, selected, used_fallback))
            if progress_callback is not None:
                progress_callback(completed_count, len(ordered_scenes))
    except Exception:
        _set_project_status(store, project_id, ProjectStatus.FAILED)
        raise
    _set_project_status(store, project_id, ProjectStatus.ASSETS_READY)
    return results
