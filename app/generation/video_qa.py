"""Quality validation for generated scene videos."""

import json
import subprocess
from pathlib import Path

from app.exceptions import VideoAgentError


def validate_scene_video(
    path: Path,
    *,
    expected_duration: float,
    expected_fps: int,
    expected_resolution: tuple[int, int],
    ffprobe_command: str = "ffprobe",
    ffmpeg_command: str = "ffmpeg",
    tolerance_seconds: float = 0.5,
) -> dict[str, object]:
    """Verify that a generated clip exists, decodes, and matches its contract."""
    if not path.is_file() or path.stat().st_size == 0:
        raise VideoAgentError(f"generated scene video is missing or empty: {path}")

    probe = [
        ffprobe_command, "-v", "error", "-show_entries",
        "format=duration:stream=codec_type,width,height,r_frame_rate",
        "-of", "json", str(path),
    ]
    try:
        inspected = subprocess.run(probe, check=False, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise VideoAgentError("ffprobe could not inspect generated scene video") from exc
    if inspected.returncode != 0:
        raise VideoAgentError(f"generated scene video failed ffprobe: {inspected.stderr.strip()}")
    try:
        payload = json.loads(inspected.stdout)
    except json.JSONDecodeError as exc:
        raise VideoAgentError("ffprobe returned invalid JSON for scene video") from exc

    streams = payload.get("streams", [])
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    if video is None:
        raise VideoAgentError("generated scene video has no video stream")

    duration = float(payload.get("format", {}).get("duration", 0))
    if abs(duration - expected_duration) > tolerance_seconds:
        raise VideoAgentError(
            f"generated scene duration {duration:.3f}s differs from expected {expected_duration:.3f}s"
        )
    width, height = expected_resolution
    if video.get("width") != width or video.get("height") != height:
        raise VideoAgentError("generated scene resolution does not match the configured output")
    if _fps(video.get("r_frame_rate")) != expected_fps:
        raise VideoAgentError("generated scene FPS does not match the configured output")

    decode = [ffmpeg_command, "-v", "error", "-i", str(path), "-f", "null", "-"]
    try:
        decoded = subprocess.run(decode, check=False, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise VideoAgentError("FFmpeg could not decode generated scene video") from exc
    if decoded.returncode != 0:
        raise VideoAgentError(f"generated scene video failed decode: {decoded.stderr.strip()}")

    return {"duration_seconds": duration, "width": width, "height": height, "fps": expected_fps}


def _fps(value: str | None) -> int:
    if not value:
        return 0
    try:
        numerator, denominator = value.split("/", 1)
        return round(int(numerator) / int(denominator))
    except (ValueError, ZeroDivisionError):
        return 0
