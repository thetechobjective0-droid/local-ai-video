"""Tests for project-level media generation orchestration."""

from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app.exceptions import VideoAgentError
from app.models.project import VideoProject
from app.models.scene import MediaType, Scene
from app.orchestrator.media_generation import generate_project_media
from app.orchestrator.media_strategy import VideoCapability
from app.providers.video import VideoGenerationRequest, VideoResult
from app.storage.filesystem import FilesystemStore


class FakeVideoProvider:
    provider_name = "fake-video"

    def __init__(self, output: Path, *, fail: bool = False) -> None:
        self.output = output
        self.fail = fail

    def generate(self, request: VideoGenerationRequest) -> VideoResult:
        if self.fail:
            raise VideoAgentError("fake provider failed")
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        request.output_path.write_bytes(b"fake-video")
        return VideoResult(
            path=request.output_path,
            provider=self.provider_name,
            model="fake-v1",
            duration_seconds=request.duration_seconds,
            fps=request.fps,
            width=704,
            height=384,
            sha256=__import__("hashlib").sha256(b"fake-video").hexdigest(),
        )


def _scene(project_id: UUID) -> Scene:
    image_id = uuid4()
    return Scene(
        index=1,
        start_seconds=0,
        duration_seconds=4,
        image_asset=image_id,
        preferred_media_type=MediaType.IMAGE_TO_VIDEO,
        fallback_media_type=MediaType.IMAGE_MOTION,
    )


def _create_project(store: FilesystemStore, project_id: UUID) -> None:
    store.write_json(
        store.project_dir(project_id),
        "project.json",
        VideoProject(
            id=project_id,
            source_prompt="test project",
            duration_seconds=4,
        ).model_dump(mode="json"),
    )


def test_project_media_uses_preferred_i2v(tmp_path: Path) -> None:
    store = FilesystemStore(tmp_path / "data")
    project_id = uuid4()
    directory = store.project_dir(project_id)
    directory.mkdir(parents=True)
    _create_project(store, project_id)
    scene = _scene(project_id)
    image_path = directory / "image.png"
    image_path.write_bytes(b"image")
    store.write_json(
        directory,
        "scene-0001-image.json",
        {
            "id": str(scene.image_asset),
            "project_id": str(project_id),
            "scene_id": str(scene.id),
            "type": "scene_image",
            "path": str(image_path),
            "mime": "image/png",
        },
    )
    provider = FakeVideoProvider(tmp_path / "out.mp4")
    results = generate_project_media(
        store,
        project_id,
        [scene],
        video_provider=provider,
        video_capability=VideoCapability(image_to_video=True, max_duration_seconds=5),
    )
    assert results[0].selected_media_type is MediaType.IMAGE_TO_VIDEO
    assert results[0].used_fallback is False


def test_project_media_falls_back_after_i2v_failure(tmp_path: Path) -> None:
    store = FilesystemStore(tmp_path / "data")
    project_id = uuid4()
    directory = store.project_dir(project_id)
    directory.mkdir(parents=True)
    _create_project(store, project_id)
    scene = _scene(project_id)
    image_path = directory / "image.png"
    image_path.write_bytes(b"image")
    store.write_json(
        directory,
        "scene-0001-image.json",
        {
            "id": str(scene.image_asset),
            "project_id": str(project_id),
            "scene_id": str(scene.id),
            "type": "scene_image",
            "path": str(image_path),
            "mime": "image/png",
        },
    )
    failing = FakeVideoProvider(tmp_path / "failed.mp4", fail=True)
    fallback = FakeVideoProvider(tmp_path / "fallback.mp4")
    results = generate_project_media(
        store,
        project_id,
        [scene],
        video_provider=failing,
        fallback_provider=fallback,
        video_capability=VideoCapability(image_to_video=True, max_duration_seconds=5),
    )
    assert results[0].selected_media_type is MediaType.IMAGE_MOTION
    assert results[0].used_fallback is True


def test_project_media_rejects_text_to_video_until_supported(tmp_path: Path) -> None:
    store = FilesystemStore(tmp_path / "data")
    project_id = uuid4()
    directory = store.project_dir(project_id)
    directory.mkdir(parents=True)
    _create_project(store, project_id)
    scene = Scene(
        index=1,
        start_seconds=0,
        duration_seconds=4,
        preferred_media_type=MediaType.TEXT_TO_VIDEO,
        fallback_media_type=MediaType.STATIC_IMAGE,
    )
    with pytest.raises(VideoAgentError, match="text-to-video routing"):
        generate_project_media(
            store,
            project_id,
            [scene],
            video_provider=FakeVideoProvider(tmp_path / "out.mp4"),
            video_capability=VideoCapability(text_to_video=True),
        )
