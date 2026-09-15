"""Deterministic local image-to-video fallback using FFmpeg."""

import hashlib
import subprocess
from pathlib import Path

from app.exceptions import ProviderUnavailableError, VideoAgentError
from app.providers.video import VideoGenerationRequest, VideoResult


class FFmpegVideoProvider:
    """Create a deterministic motion clip from a local still image.

    This provider is deliberately not an AI video synthesizer. It is available
    only as an explicitly selected or explicitly enabled fallback path.
    """

    provider_name = "ffmpeg_ken_burns"
    model_name = "ffmpeg-motion-v1"

    def __init__(self, *, ffmpeg_command: str = "ffmpeg") -> None:
        self.ffmpeg_command = ffmpeg_command

    def generate(self, request: VideoGenerationRequest) -> VideoResult:
        if not request.image_path.is_file():
            raise VideoAgentError(f"Input image does not exist: {request.image_path}")
        if request.duration_seconds <= 0:
            raise ValueError("Video duration must be positive")
        if request.fps <= 0:
            raise ValueError("Video FPS must be positive")

        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        frames = max(1, round(request.duration_seconds * request.fps))
        vf = (
            f"scale=ceil(iw/2)*2:ceil(ih/2)*2,"
            f"zoompan=z='min(zoom+0.0008,1.12)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s=iwxih:fps={request.fps},format=yuv420p"
        )
        command = [
            self.ffmpeg_command,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-loop",
            "1",
            "-i",
            str(request.image_path),
            "-vf",
            vf,
            "-frames:v",
            str(frames),
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(request.output_path),
        ]
        try:
            completed = subprocess.run(
                command, check=False, capture_output=True, text=True, timeout=300
            )
        except subprocess.TimeoutExpired as exc:
            raise ProviderUnavailableError("FFmpeg video generation timed out") from exc
        except OSError as exc:
            raise ProviderUnavailableError("FFmpeg is unavailable") from exc
        if completed.returncode != 0:
            detail = completed.stderr.strip() or "unknown FFmpeg error"
            raise VideoAgentError(f"FFmpeg video generation failed: {detail}")
        if not request.output_path.is_file() or request.output_path.stat().st_size == 0:
            raise VideoAgentError("FFmpeg returned no usable video file")

        duration = frames / request.fps
        width, height = _probe_dimensions(request.output_path)
        digest = hashlib.sha256(request.output_path.read_bytes()).hexdigest()
        return VideoResult(
            path=request.output_path,
            provider=self.provider_name,
            model=self.model_name,
            duration_seconds=duration,
            fps=request.fps,
            width=width,
            height=height,
            sha256=digest,
            metadata={
                **request.metadata,
                "generation_mode": "image_motion",
                "temporal_generation": False,
            },
        )


def _probe_dimensions(path: Path) -> tuple[int, int]:
    """Read dimensions with ffprobe when available."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "csv=p=0:s=x",
                str(path),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProviderUnavailableError("ffprobe is unavailable") from exc
    if result.returncode != 0:
        raise VideoAgentError("Unable to probe generated video dimensions")
    try:
        width_text, height_text = result.stdout.strip().split("x", 1)
        width, height = int(width_text), int(height_text)
    except (ValueError, AttributeError) as exc:
        raise VideoAgentError("ffprobe returned invalid video dimensions") from exc
    if width <= 0 or height <= 0:
        raise VideoAgentError("Generated video has invalid dimensions")
    return width, height
