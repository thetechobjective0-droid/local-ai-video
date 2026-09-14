"""Assemble per-scene narration into a normalized project audio track."""

import hashlib
import struct
import wave
from pathlib import Path
from uuid import UUID

from app.exceptions import VideoAgentError
from app.models.artifact import Artifact
from app.storage.filesystem import FilesystemStore


def assemble_narration_track(
    store: FilesystemStore,
    project_id: UUID,
    *,
    normalize_peak: float = 0.95,
) -> Artifact:
    """Concatenate scene WAV files in index order and apply peak normalization."""
    if not 0 < normalize_peak <= 1:
        raise ValueError("normalize_peak must be greater than 0 and at most 1")
    directory = store.project_dir(project_id)
    audio_dir = directory / "audio"
    inputs = sorted(audio_dir.glob("scene-*.wav"))
    if not inputs:
        raise VideoAgentError("no scene narration WAV files found")

    frames, sample_rate, channels, sample_width = _read_pcm_files(inputs)
    normalized = _normalize_pcm(frames, sample_width, normalize_peak)
    output = audio_dir / "narration.wav"
    with wave.open(str(output), "wb") as audio:
        audio.setnchannels(channels)
        audio.setsampwidth(sample_width)
        audio.setframerate(sample_rate)
        audio.writeframes(normalized)

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    duration = len(normalized) / (sample_rate * channels * sample_width)
    artifact = Artifact(
        project_id=project_id,
        type="narration_track",
        path=output,
        mime="audio/wav",
        provider="local",
        model="assembled-scene-narration",
        sha256=digest,
        parameters={
            "scene_count": len(inputs),
            "duration_seconds": duration,
            "sample_rate": sample_rate,
            "channels": channels,
            "sample_width": sample_width,
            "peak": normalize_peak,
        },
    )
    store.write_json(directory, "narration.json", artifact.model_dump(mode="json"))
    return artifact


def _read_pcm_files(paths: list[Path]) -> tuple[bytes, int, int, int]:
    chunks: list[bytes] = []
    audio_format: tuple[int, int, int] | None = None
    for path in paths:
        try:
            with wave.open(str(path), "rb") as audio:
                current = (audio.getframerate(), audio.getnchannels(), audio.getsampwidth())
                if audio_format is None:
                    audio_format = current
                elif current != audio_format:
                    raise VideoAgentError("scene narration files use incompatible WAV formats")
                chunks.append(audio.readframes(audio.getnframes()))
        except (wave.Error, OSError) as exc:
            raise VideoAgentError(f"invalid scene narration file: {path.name}") from exc
    if audio_format is None:
        raise VideoAgentError("no readable scene narration files found")
    return b"".join(chunks), *audio_format


def _normalize_pcm(data: bytes, sample_width: int, target_peak: float) -> bytes:
    if sample_width != 2:
        return data
    samples = struct.unpack(f"<{len(data) // 2}h", data)
    peak = max((abs(sample) for sample in samples), default=0)
    if peak == 0:
        return data
    scale = target_peak * 32767 / peak
    normalized = [max(-32768, min(32767, round(sample * scale))) for sample in samples]
    return struct.pack(f"<{len(normalized)}h", *normalized)
