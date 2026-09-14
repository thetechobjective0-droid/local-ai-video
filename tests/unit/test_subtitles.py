"""Tests for deterministic subtitle generation."""

from uuid import uuid4

from app.generation.subtitles import build_subtitles
from app.models.scene import Scene
from app.storage.filesystem import FilesystemStore


def test_build_subtitles_writes_srt_and_vtt(tmp_path) -> None:
    project_id = uuid4()
    store = FilesystemStore(tmp_path)
    directory = store.project_dir(project_id)
    directory.mkdir(parents=True)
    scenes = [
        Scene(
            index=1,
            start_seconds=0,
            duration_seconds=4,
            narration="A short introduction to local AI video generation.",
        ),
        Scene(
            index=2,
            start_seconds=4,
            duration_seconds=3,
            narration="The pipeline then renders the result.",
        ),
    ]

    outputs = build_subtitles(store, project_id, scenes, max_chars=30)

    assert set(outputs) == {"srt", "vtt"}
    srt = outputs["srt"].read_text(encoding="utf-8")
    vtt = outputs["vtt"].read_text(encoding="utf-8")
    assert srt.startswith("1\n00:00:00,000 --> ")
    assert "The pipeline then renders the" in srt
    assert "result." in srt
    assert vtt.startswith("WEBVTT\n\n")
    assert "00:00:04." in vtt


def test_build_subtitles_skips_empty_narration(tmp_path) -> None:
    project_id = uuid4()
    store = FilesystemStore(tmp_path)
    directory = store.project_dir(project_id)
    directory.mkdir(parents=True)
    scenes = [Scene(index=1, start_seconds=0, duration_seconds=2, narration="")]

    outputs = build_subtitles(store, project_id, scenes)

    assert outputs["srt"].read_text(encoding="utf-8") == ""
    assert outputs["vtt"].read_text(encoding="utf-8") == "WEBVTT\n\n"
