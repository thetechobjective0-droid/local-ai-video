"""Bounded image-generation recovery with deterministic prompt refinement."""

from dataclasses import dataclass
from uuid import UUID

from app.exceptions import VideoAgentError
from app.generation.images import generate_scene_image
from app.models.scene import Scene
from app.recovery import IMAGE_RETRY_POLICY, run_bounded
from app.providers.image import ImageProvider
from app.storage.filesystem import FilesystemStore


@dataclass(frozen=True)
class ImageRecoveryResult:
    """Generated scene image plus bounded recovery metadata."""

    scene: Scene
    attempts: int
    strategies: tuple[str, ...]


def _simplify_prompt(prompt: str) -> str:
    """Apply a deterministic, conservative prompt simplification."""
    text = " ".join(prompt.split())
    if not text:
        return "Create a clear cinematic image matching the scene description."
    return text[:600]


def generate_scene_image_with_recovery(
    provider: ImageProvider,
    store: FilesystemStore,
    project_id: UUID,
    scene: Scene,
    **kwargs: object,
) -> ImageRecoveryResult:
    """Generate an image with a finite budget and deterministic refinement."""
    original_prompt = scene.image_prompt
    strategies: list[str] = []

    def operation(attempt: int) -> Scene:
        if attempt == 0:
            current = scene
            strategies.append("original")
        elif attempt == 1:
            current = scene.model_copy(
                update={
                    "image_prompt": _simplify_prompt(original_prompt or scene.visual_description)
                }
            )
            strategies.append("simplified_prompt")
        else:
            current = scene.model_copy(
                update={"image_prompt": _simplify_prompt(scene.visual_description)}
            )
            strategies.append("visual_description_fallback")
        _, updated = generate_scene_image(provider, store, project_id, current, **kwargs)
        return updated

    try:
        result = run_bounded(operation, IMAGE_RETRY_POLICY)
    except Exception as exc:
        raise VideoAgentError(
            f"scene image generation failed after bounded recovery: {exc}"
        ) from exc
    return ImageRecoveryResult(result.value, result.attempts, tuple(strategies))
