"""Generate and persist one image artifact for an individual scene."""

from pathlib import Path
from uuid import UUID

from app.models.artifact import Artifact
from app.models.scene import Scene
from app.providers.image import ImageGenerationRequest, ImageProvider
from app.storage.filesystem import FilesystemStore


def generate_scene_image(
    provider: ImageProvider,
    store: FilesystemStore,
    project_id: UUID,
    scene: Scene,
    *,
    model: str | None = None,
    width: int = 1024,
    height: int = 576,
    steps: int = 30,
    guidance_scale: float = 7.0,
    seed: int | None = None,
) -> tuple[Artifact, Scene]:
    """Generate a scene image and persist its metadata atomically."""
    directory = store.project_dir(project_id)
    if not directory.is_dir():
        raise ValueError(f"project does not exist: {project_id}")

    images_dir = directory / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    output = images_dir / f"scene-{scene.index:04d}.png"
    result = provider.generate(
        ImageGenerationRequest(
            prompt=scene.image_prompt or scene.visual_description,
            negative_prompt=scene.negative_prompt,
            output_path=output,
            model=model,
            width=width,
            height=height,
            steps=steps,
            guidance_scale=guidance_scale,
            seed=seed,
            metadata={"scene_id": str(scene.id), "scene_index": scene.index},
        )
    )

    artifact = Artifact(
        project_id=project_id,
        scene_id=scene.id,
        type="scene_image",
        path=result.path,
        mime="image/png",
        provider=result.provider,
        model=result.model,
        sha256=result.sha256,
        parameters={
            "width": result.width,
            "height": result.height,
            "steps": steps,
            "guidance_scale": guidance_scale,
            "seed": result.seed,
            **result.metadata,
        },
    )
    store.write_json(
        directory,
        f"scene-{scene.index:04d}-image.json",
        artifact.model_dump(mode="json"),
    )
    updated_scene = scene.model_copy(
        update={"image_asset": artifact.id, "status": "ready"}
    )
    store.write_json(
        directory,
        f"scene-{scene.index:04d}.json",
        updated_scene.model_dump(mode="json"),
    )
    return artifact, updated_scene
