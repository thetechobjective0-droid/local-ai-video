"""Deterministic integrity checks for generated media artifacts."""

import hashlib
import json
import struct
import subprocess
from pathlib import Path

from app.exceptions import VideoAgentError


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def validate_image(
    path: Path,
    *,
    expected_width: int | None = None,
    expected_height: int | None = None,
) -> dict[str, object]:
    """Validate a PNG's existence, signature, IHDR dimensions, and non-empty payload."""
    if not path.is_file() or path.stat().st_size <= len(PNG_SIGNATURE):
        raise VideoAgentError(f"image artifact is missing or empty: {path}")
    try:
        with path.open("rb") as handle:
            signature = handle.read(8)
            length_data = handle.read(4)
            chunk_type = handle.read(4)
            ihdr = handle.read(13)
    except OSError as exc:
        raise VideoAgentError(f"image artifact cannot be read: {path}") from exc
    if signature != PNG_SIGNATURE or length_data != struct.pack(">I", 13) or chunk_type != b"IHDR":
        raise VideoAgentError(f"image artifact is not a valid PNG: {path}")
    width, height = struct.unpack(">II", ihdr[:8])
    if width <= 0 or height <= 0:
        raise VideoAgentError("image artifact has invalid dimensions")
    if expected_width is not None and width != expected_width:
        raise VideoAgentError(f"image width {width} does not match expected {expected_width}")
    if expected_height is not None and height != expected_height:
        raise VideoAgentError(f"image height {height} does not match expected {expected_height}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"width": width, "height": height, "sha256": digest}


def validate_audio(
    path: Path,
    *,
    expected_duration: float | None = None,
    tolerance_seconds: float = 0.5,
    ffprobe_command: str = "ffprobe",
) -> dict[str, object]:
    """Validate audio decoding, duration, and presence of an audio stream."""
    if not path.is_file() or path.stat().st_size == 0:
        raise VideoAgentError(f"audio artifact is missing or empty: {path}")
    command = [
        ffprobe_command,
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=codec_type,sample_rate,channels:format=duration",
        "-of",
        "json",
        str(path),
    ]
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise VideoAgentError("ffprobe could not inspect audio artifact") from exc
    if completed.returncode != 0:
        raise VideoAgentError(f"audio artifact failed ffprobe: {completed.stderr.strip()}")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise VideoAgentError("ffprobe returned invalid audio JSON") from exc
    streams = payload.get("streams", [])
    if not streams or streams[0].get("codec_type") != "audio":
        raise VideoAgentError("audio artifact has no audio stream")
    duration = float(payload.get("format", {}).get("duration", 0))
    if duration <= 0:
        raise VideoAgentError("audio artifact has non-positive duration")
    if expected_duration is not None and abs(duration - expected_duration) > tolerance_seconds:
        raise VideoAgentError(
            f"audio duration {duration:.3f}s differs from expected {expected_duration:.3f}s"
        )
    return {"duration_seconds": duration, "audio_stream": streams[0]}
