"""Tests for deterministic timeline construction."""

from uuid import uuid4

import pytest

from app.exceptions import VideoAgentError
from app.generation.timeline import build_timeline
from app.models.project import VideoProject
from app.models.scene import Scene
from app.storage.filesystem import FilesystemStore


def test_build_timeline_persists_scene_order_and_media(tmp_path) -> None:
    project = VideoProject(id=uuid4(), source_prompt="demo", duration_seconds=7)
    store = FilesystemStore(tmp_path)
    store.create_project(project)
    audio_id = uuid4()
    image_id = uuid4()
    scenes = [
        Scene(
            index=2, start_seconds=4, duration_seconds=3, narration="Second", audio_asset=audio_id
        ),
        Scene(
            index=1, start_seconds=0, duration_seconds=4, narration="First", image_asset=image_id
        ),
    ]

    timeline = build_timeline(store, project, scenes)

    assert [entry.index for entry in timeline.scenes] == [1, 2]
    assert timeline.scenes[0].image_asset == image_id
    assert timeline.scenes[1].audio_asset == audio_id
    assert (store.project_dir(project.id) / "timeline.json").exists()


def test_build_timeline_rejects_overlap(tmp_path) -> None:
    project = VideoProject(id=uuid4(), source_prompt="demo", duration_seconds=7)
    store = FilesystemStore(tmp_path)
    store.create_project(project)
    scenes = [
        Scene(index=1, start_seconds=0, duration_seconds=5),
        Scene(index=2, start_seconds=4, duration_seconds=2),
    ]

    with pytest.raises(VideoAgentError, match="overlaps"):
        build_timeline(store, project, scenes)
