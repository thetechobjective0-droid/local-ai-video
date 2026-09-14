"""Tests for scene video orchestration."""

import hashlib
from pathlib import Path
from uuid import uuid4

from app.generation.video import generate_scene_video
from app.models.artifact import Artifact
from app.models.scene import Scene
from app.providers.video import VideoGenerationRequest, VideoResult
from app.storage.filesystem import FilesystemStore


class FakeVideoProvider:
    def generate(self, request: VideoGenerationRequest) -> VideoResult:
        request.output_path.write_bytes(b"fake-video")
        digest = hashlib.sha256(b"fake-video").hexdigest()
        return VideoResult(
            path=request.output_path,
            provider="fake-video",
            model="fake-v1",
            duration_seconds=request.duration_seconds,
            fps=request.fps,
            width=1024,
            height=576,
            sha256=digest,
        )


def test_generate_scene_video_persists_artifact_and_scene(tmp_path: Path) -> None:
    project_id = uuid4()
    store = FilesystemStore(tmp_path)
    project_dir = store.project_dir(project_id)
    project_dir.mkdir(parents=True)
    image = project_dir / "images" / "scene-0001.png"
    image.parent.mkdir()
    image.write_bytes(b"image")
    scene = Scene(
        index=1,
        start_seconds=0,
        duration_seconds=4,
        image_asset=uuid4(),
        motion_prompt="slow camera push",
    )
    store.write_json(project_dir, "scene-0001.json", scene.model_dump(mode="json"))
    store.write_json(
        project_dir,
        "scene-0001-image.json",
        Artifact(
            project_id=project_id,
            scene_id=scene.id,
            type="scene_image",
            path=image,
            mime="image/png",
        ).model_dump(mode="json"),
    )

    artifact, updated = generate_scene_video(FakeVideoProvider(), store, project_id, scene, fps=12)

    assert artifact.type == "scene_video"
    assert artifact.path == project_dir / "videos" / "scene-0001.mp4"
    assert updated.video_asset == artifact.id
    assert artifact.sha256 == hashlib.sha256(b"fake-video").hexdigest()
    assert (project_dir / "scene-0001-video.json").is_file()


def test_generate_scene_video_requires_image_asset(tmp_path: Path) -> None:
    project_id = uuid4()
    store = FilesystemStore(tmp_path)
    store.project_dir(project_id).mkdir(parents=True)
    scene = Scene(index=1, start_seconds=0, duration_seconds=4)

    try:
        generate_scene_video(FakeVideoProvider(), store, project_id, scene)
    except Exception as exc:
        assert "image asset" in str(exc)
    else:
        raise AssertionError("expected missing image asset to fail")
