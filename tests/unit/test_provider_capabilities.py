"""Tests for centralized local provider capabilities."""

import pytest

from app.providers.capabilities import get_provider_capabilities


def test_ffmpeg_provider_exposes_deterministic_motion() -> None:
    capabilities = get_provider_capabilities("ffmpeg_ken_burns")
    assert capabilities.video.image_motion is True
    assert capabilities.video.image_to_video is False
    assert capabilities.video.memory_class == "low"


def test_ltx_provider_exposes_bounded_image_to_video() -> None:
    capabilities = get_provider_capabilities("ltx_video")
    assert capabilities.video.image_motion is False
    assert capabilities.video.image_to_video is True
    assert capabilities.video.max_duration_seconds == 20
    assert capabilities.video.memory_class == "high"


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported local video provider"):
        get_provider_capabilities("unknown")
