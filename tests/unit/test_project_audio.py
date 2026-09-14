"""Tests for project narration assembly."""

import wave
from pathlib import Path
from uuid import uuid4

from app.generation.project_audio import assemble_narration_track
from app.storage.filesystem import FilesystemStore


def _write_wav(path: Path, frames: int) -> None:
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(22050)
        audio.writeframes(b"\x10\x00" * frames)


def test_assemble_narration_track_concatenates_and_persists(tmp_path: Path) -> None:
    store = FilesystemStore(tmp_path / "data")
    project_id = uuid4()
    directory = store.project_dir(project_id)
    audio_dir = directory / "audio"
    audio_dir.mkdir(parents=True)
    _write_wav(audio_dir / "scene-0002.wav", 2205)
    _write_wav(audio_dir / "scene-0001.wav", 4410)

    artifact = assemble_narration_track(store, project_id)

    assert artifact.type == "narration_track"
    assert artifact.sha256
    with wave.open(str(audio_dir / "narration.wav"), "rb") as audio:
        assert audio.getnframes() == 6615
        assert audio.getframerate() == 22050
    assert (directory / "narration.json").is_file()
