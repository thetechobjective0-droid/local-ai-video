"""Bounded video-generation recovery and deterministic fallback policy."""

from dataclasses import dataclass
from uuid import UUID

from app.exceptions import VideoAgentError
from app.generation.video import generate_scene_video
from app.models.scene import Scene
from app.recovery import VIDEO_RETRY_POLICY, run_bounded
from app.providers.video import VideoProvider
from app.storage.filesystem import FilesystemStore


@dataclass(frozen=True)
class VideoRecoveryResult:
    """Generated scene video plus recovery metadata."""

    scene: Scene
    attempts: int
    strategies: tuple[str, ...]


def _bounded_duration(duration: float, attempt: int) -> float:
    """Reduce clip duration conservatively for later attempts."""
    if attempt == 0:
        return duration
    if attempt == 1:
        return max(1.0, round(duration * 0.75, 3))
    return max(1.0, round(duration * 0.5, 3))


def generate_scene_video_with_recovery(
    provider: VideoProvider,
    store: FilesystemStore,
    project_id: UUID,
    scene: Scene,
    **kwargs: object,
) -> VideoRecoveryResult:
    """Generate scene video with finite duration refinement and provider fallback."""
    strategies: list[str] = []

    def operation(attempt: int) -> Scene:
        duration = _bounded_duration(scene.duration_seconds, attempt)
        current = scene.model_copy(update={"duration_seconds": duration})
        if attempt == 0:
            strategies.append("original")
        elif attempt == 1:
            strategies.append("reduced_duration")
        else:
            strategies.append("reduced_duration_aggressive")
        _, updated = generate_scene_video(provider, store, project_id, current, **kwargs)
        return updated

    try:
        result = run_bounded(operation, VIDEO_RETRY_POLICY)
    except Exception as exc:
        raise VideoAgentError(f"scene video generation failed after bounded recovery: {exc}") from exc
    return VideoRecoveryResult(result.value, result.attempts, tuple(strategies))
