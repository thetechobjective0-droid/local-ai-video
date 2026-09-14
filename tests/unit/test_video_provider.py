"""Tests for the local motion-video provider."""

from pathlib import Path

import pytest

from app.exceptions import VideoAgentError
from app.providers.ffmpeg_video import FFmpegVideoProvider
from app.providers.video import VideoGenerationRequest


def test_video_provider_rejects_missing_image(tmp_path: Path) -> None:
    provider = FFmpegVideoProvider(ffmpeg_command="ffmpeg")
    request = VideoGenerationRequest(
        image_path=tmp_path / "missing.png",
        output_path=tmp_path / "scene.mp4",
    )
    with pytest.raises(VideoAgentError, match="Input image does not exist"):
        provider.generate(request)


def test_video_provider_rejects_invalid_duration(tmp_path: Path) -> None:
    image = tmp_path / "scene.png"
    image.write_bytes(b"not-an-image")
    request = VideoGenerationRequest(
        image_path=image,
        output_path=tmp_path / "scene.mp4",
        duration_seconds=0,
    )
    with pytest.raises(ValueError, match="duration"):
        FFmpegVideoProvider().generate(request)
