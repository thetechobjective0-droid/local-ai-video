"""Tests for scene-level local narration generation."""

import hashlib
import wave
from pathlib import Path
from uuid import uuid4

from app.generation.audio import generate_scene_audio
from app.models.scene import Scene
from app.providers.tts import TTSRequest, TTSResult
from app.storage.filesystem import FilesystemStore


class FakeTTSProvider:
    def synthesize(self, request: TTSRequest) -> TTSResult:
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(request.output_path), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(22050)
            audio.writeframes(b"\x00\x00" * 22050)
        digest = hashlib.sha256(request.output_path.read_bytes()).hexdigest()
        return TTSResult(
            path=request.output_path,
            provider="fake",
            model="fake-tts",
            voice=request.voice,
            duration_seconds=1.0,
            sample_rate=22050,
            channels=1,
            sha256=digest,
        )


def test_generate_scene_audio_persists_artifact_and_scene(tmp_path: Path) -> None:
    store = FilesystemStore(tmp_path / "data")
    project_id = uuid4()
    directory = store.project_dir(project_id)
    directory.mkdir(parents=True)
    scene = Scene(index=1, start_seconds=0, duration_seconds=3, narration="Hello world")

    artifact, updated = generate_scene_audio(FakeTTSProvider(), store, project_id, scene)

    assert artifact.type == "scene_audio"
    assert artifact.mime == "audio/wav"
    assert artifact.sha256
    assert updated.audio_asset == artifact.id
    assert (directory / "audio" / "scene-0001.wav").is_file()
    assert (directory / "scene-0001-audio.json").is_file()
    assert (directory / "scene-0001.json").is_file()
