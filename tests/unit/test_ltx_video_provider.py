"""Boundary tests for the local LTX video provider."""

from pathlib import Path

import pytest

from app.exceptions import ProviderUnavailableError, VideoAgentError
from app.providers.ltx_video import LTXVideoProvider
from app.providers.video import VideoGenerationRequest


def test_missing_model_is_rejected(tmp_path: Path) -> None:
    provider = LTXVideoProvider(tmp_path / "missing-model")
    request = VideoGenerationRequest(
        image_path=tmp_path / "image.png",
        output_path=tmp_path / "output.mp4",
    )
    with pytest.raises(VideoAgentError):
        provider.generate(request)


def test_missing_model_fails_before_dependency_load(tmp_path: Path) -> None:
    provider = LTXVideoProvider(tmp_path / "missing-model")
    with pytest.raises(ProviderUnavailableError):
        provider._load_pipeline()


def test_invalid_duration_is_rejected(tmp_path: Path) -> None:
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    image = tmp_path / "image.png"
    image.write_bytes(b"not-an-image")
    provider = LTXVideoProvider(model_dir)
    request = VideoGenerationRequest(
        image_path=image,
        output_path=tmp_path / "output.mp4",
        duration_seconds=0,
    )
    with pytest.raises(ValueError):
        provider.generate(request)
