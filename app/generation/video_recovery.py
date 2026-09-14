"""Bounded video-generation recovery with deterministic prompt refinement."""

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


def _simplify_motion_prompt(prompt: str) -> str:
    """Apply a deterministic conservative simplification to a motion prompt."""
    text = " ".join(prompt.split())
    if not text:
        return "Subtle cinematic camera motion with stable subjects and natural movement."
    return text[:600]


def generate_scene_video_with_recovery(
    provider: VideoProvider,
    store: FilesystemStore,
    project_id: UUID,
    scene: Scene,
    **kwargs: object,
) -> VideoRecoveryResult:
    """Generate a scene video with finite prompt refinement and no timing mutation."""
    original_prompt = scene.motion_prompt
    strategies: list[str] = []

    def operation(attempt: int) -> Scene:
        if attempt == 0:
            current = scene
            strategies.append("original")
        elif attempt == 1:
            current = scene.model_copy(
                update={"motion_prompt": _simplify_motion_prompt(original_prompt)}
            )
            strategies.append("simplified_motion_prompt")
        else:
            current = scene.model_copy(
                update={
                    "motion_prompt": "Subtle cinematic motion; preserve composition and subject identity.",
                    "negative_prompt": "",
                }
            )
            strategies.append("conservative_motion_prompt")
        _, updated = generate_scene_video(provider, store, project_id, current, **kwargs)
        return updated

    try:
        result = run_bounded(operation, VIDEO_RETRY_POLICY)
    except Exception as exc:
        raise VideoAgentError(
            f"scene video generation failed after bounded recovery: {exc}"
        ) from exc
    return VideoRecoveryResult(result.value, result.attempts, tuple(strategies))
