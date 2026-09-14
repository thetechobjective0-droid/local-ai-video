"""Post-render validation for local video outputs."""

import json
import subprocess
from pathlib import Path

from app.exceptions import VideoAgentError


def validate_video(
    path: Path,
    *,
    expected_duration: float,
    expected_fps: int,
    expected_resolution: str,
    require_audio: bool = True,
    tolerance_seconds: float = 0.5,
    ffprobe_command: str = "ffprobe",
) -> dict[str, object]:
    """Validate existence, decodability, streams, duration, FPS, and resolution."""
    if not path.is_file() or path.stat().st_size == 0:
        raise VideoAgentError(f"rendered video is missing or empty: {path}")
    command = [
        ffprobe_command,
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=index,codec_type,width,height,r_frame_rate",
        "-of",
        "json",
        str(path),
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise VideoAgentError("ffprobe could not inspect rendered video") from exc
    if completed.returncode != 0:
        raise VideoAgentError(f"rendered video failed ffprobe: {completed.stderr.strip()}")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise VideoAgentError("ffprobe returned invalid JSON") from exc

    streams = payload.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    if video is None:
        raise VideoAgentError("rendered video has no video stream")
    if require_audio and audio is None:
        raise VideoAgentError("rendered video has no audio stream")

    duration = float(payload.get("format", {}).get("duration", 0))
    if abs(duration - expected_duration) > tolerance_seconds:
        raise VideoAgentError(
            f"rendered duration {duration:.3f}s differs from expected {expected_duration:.3f}s"
        )
    width, height = _resolution(expected_resolution)
    if video.get("width") != width or video.get("height") != height:
        raise VideoAgentError(
            f"rendered resolution {video.get('width')}x{video.get('height')} does not match "
            f"{expected_resolution}"
        )
    if _fps(video.get("r_frame_rate")) != expected_fps:
        raise VideoAgentError("rendered FPS does not match the timeline")
    return {"duration_seconds": duration, "video_stream": video, "audio_stream": audio}


def _resolution(value: str) -> tuple[int, int]:
    try:
        width, height = value.lower().split("x", 1)
        return int(width), int(height)
    except ValueError as exc:
        raise ValueError(f"invalid resolution: {value}") from exc


def _fps(value: str | None) -> int:
    if not value:
        return 0
    try:
        numerator, denominator = value.split("/", 1)
        return round(int(numerator) / int(denominator))
    except (ValueError, ZeroDivisionError):
        return 0
