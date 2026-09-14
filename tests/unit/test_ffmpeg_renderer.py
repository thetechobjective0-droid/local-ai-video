"""Tests for deterministic FFmpeg rendering boundaries."""

import json
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from app.models.artifact import Artifact
from app.models.timeline import Timeline, TimelineScene
from app.render.ffmpeg import FFmpegRenderer, _load_artifacts
from app.storage.filesystem import FilesystemStore


def test_renderer_builds_local_ffmpeg_command(tmp_path: Path) -> None:
    project_id = uuid4()
    store = FilesystemStore(tmp_path / "data")
    directory = store.project_dir(project_id)
    directory.mkdir(parents=True)
    image = directory / "image.png"
    audio = directory / "audio.wav"
    image.write_bytes(b"png")
    audio.write_bytes(b"wav")
    image_id = uuid4()
    audio_id = uuid4()
    store.write_json(
        directory,
        "image-artifact.json",
        Artifact(
            project_id=project_id, id=image_id, type="scene_image", path=image, mime="image/png"
        ).model_dump(mode="json"),
    )
    store.write_json(
        directory,
        "audio-artifact.json",
        Artifact(
            project_id=project_id, id=audio_id, type="scene_audio", path=audio, mime="audio/wav"
        ).model_dump(mode="json"),
    )
    timeline = Timeline(
        project_id=project_id,
        duration_seconds=2,
        fps=30,
        resolution="1920x1080",
        scenes=[
            TimelineScene(
                scene_id=uuid4(),
                index=1,
                start_seconds=0,
                duration_seconds=2,
                image_asset=image_id,
                audio_asset=audio_id,
            )
        ],
    )

    command, filter_complex = FFmpegRenderer()._build_command(
        directory, timeline, _load_artifacts(directory), directory / "final.mp4"
    )

    assert command[0] == "ffmpeg"
    assert "-filter_complex" in command
    assert "concat=n=1:v=1:a=1" in filter_complex


def test_renderer_persists_validated_final_artifact(tmp_path: Path) -> None:
    project_id = uuid4()
    store = FilesystemStore(tmp_path / "data")
    directory = store.project_dir(project_id)
    directory.mkdir(parents=True)
    image = directory / "image.png"
    audio = directory / "audio.wav"
    image.write_bytes(b"png")
    audio.write_bytes(b"wav")
    image_id = uuid4()
    audio_id = uuid4()
    store.write_json(
        directory,
        "image.json",
        Artifact(project_id=project_id, id=image_id, type="scene_image", path=image).model_dump(
            mode="json"
        ),
    )
    store.write_json(
        directory,
        "audio.json",
        Artifact(project_id=project_id, id=audio_id, type="scene_audio", path=audio).model_dump(
            mode="json"
        ),
    )
    timeline = Timeline(
        project_id=project_id,
        duration_seconds=2,
        fps=30,
        resolution="1920x1080",
        scenes=[
            TimelineScene(
                scene_id=uuid4(),
                index=1,
                start_seconds=0,
                duration_seconds=2,
                image_asset=image_id,
                audio_asset=audio_id,
            )
        ],
    )
    output = directory / "final.mp4"
    output.write_bytes(b"mp4")

    completed = type("Completed", (), {"returncode": 0, "stderr": "", "stdout": ""})()
    probe = {
        "format": {"duration": "2.0"},
        "streams": [
            {"codec_type": "video", "width": 1920, "height": 1080, "r_frame_rate": "30/1"},
            {"codec_type": "audio"},
        ],
    }
    with (
        patch("app.render.ffmpeg.subprocess.run", return_value=completed),
        patch(
            "app.render.validator.subprocess.run",
            return_value=type(
                "Probe", (), {"returncode": 0, "stderr": "", "stdout": json.dumps(probe)}
            )(),
        ),
    ):
        artifact = FFmpegRenderer().render(store, project_id, timeline)

    assert artifact.type == "final_video"
    assert artifact.mime == "video/mp4"
    assert (directory / "final-video.json").is_file()
