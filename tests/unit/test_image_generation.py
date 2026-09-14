from pathlib import Path
from uuid import uuid4

from app.generation.images import generate_scene_image
from app.models.scene import Scene
from app.providers.image import ImageGenerationRequest, ImageResult
from app.storage.filesystem import FilesystemStore


class FakeImageProvider:
    def generate(self, request: ImageGenerationRequest) -> ImageResult:
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        request.output_path.write_bytes(b"valid-png-placeholder")
        return ImageResult(
            path=request.output_path,
            model="fake-model",
            provider="fake",
            width=request.width,
            height=request.height,
            seed=request.seed,
            sha256="placeholder",
            metadata={"steps": request.steps},
        )


def test_generate_scene_image_persists_artifact_and_scene(tmp_path: Path) -> None:
    project_id = uuid4()
    store = FilesystemStore(tmp_path, minimum_free_bytes=0)
    project_dir = store.project_dir(project_id)
    project_dir.mkdir(parents=True)
    scene = Scene(
        index=1,
        start_seconds=0,
        duration_seconds=5,
        visual_description="A sunrise over mountains",
        image_prompt="cinematic sunrise over mountains",
    )

    artifact, updated = generate_scene_image(
        FakeImageProvider(), store, project_id, scene, seed=42
    )

    assert artifact.project_id == project_id
    assert artifact.scene_id == scene.id
    assert artifact.type == "scene_image"
    assert artifact.sha256 == "placeholder"
    assert updated.image_asset == artifact.id
    assert updated.status.value == "ready"
    assert (project_dir / "images" / "scene-0001.png").exists()
    assert (project_dir / "scene-0001-image.json").exists()
    assert (project_dir / "scene-0001.json").exists()
