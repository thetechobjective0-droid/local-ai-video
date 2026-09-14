"""Deterministic scene-level media strategy selection."""

from dataclasses import dataclass

from app.models.scene import MediaType, Scene


@dataclass(frozen=True)
class VideoCapability:
    """Capabilities and conservative limits exposed to the routing layer."""

    image_motion: bool = False
    image_to_video: bool = False
    text_to_video: bool = False
    max_duration_seconds: float = 0.0
    memory_class: str = "low"


def select_media_type(
    scene: Scene,
    *,
    video: VideoCapability,
    available_memory_gb: float | None = None,
) -> MediaType:
    """Select a renderable media mode without using an LLM."""
    candidates = [scene.preferred_media_type, scene.fallback_media_type]
    if MediaType.IMAGE_MOTION not in candidates:
        candidates.append(MediaType.IMAGE_MOTION)
    if MediaType.STATIC_IMAGE not in candidates:
        candidates.append(MediaType.STATIC_IMAGE)

    for candidate in candidates:
        if candidate is MediaType.TEXT_TO_VIDEO and video.text_to_video:
            if _video_memory_allowed(video, available_memory_gb):
                return candidate
        if candidate is MediaType.IMAGE_TO_VIDEO and video.image_to_video:
            if scene.duration_seconds <= video.max_duration_seconds and _video_memory_allowed(
                video, available_memory_gb
            ):
                return candidate
        if candidate is MediaType.IMAGE_MOTION and video.image_motion:
            return candidate
        if candidate is MediaType.STATIC_IMAGE:
            return candidate

    return MediaType.STATIC_IMAGE


def _video_memory_allowed(capability: VideoCapability, available_memory_gb: float | None) -> bool:
    """Apply a conservative memory gate to heavyweight local video providers."""
    if capability.memory_class != "high" or available_memory_gb is None:
        return True
    return available_memory_gb >= 8.0
