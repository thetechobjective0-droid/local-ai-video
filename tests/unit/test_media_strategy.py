"""Tests for deterministic scene media routing."""

from app.models.scene import MediaType, Scene
from app.orchestrator.media_strategy import VideoCapability, select_media_type


def test_prefers_image_to_video_when_supported() -> None:
    scene = Scene(
        index=1,
        start_seconds=0,
        duration_seconds=4,
        preferred_media_type=MediaType.IMAGE_TO_VIDEO,
        fallback_media_type=MediaType.IMAGE_MOTION,
    )
    selected = select_media_type(
        scene,
        video=VideoCapability(image_to_video=True, max_duration_seconds=5),
    )
    assert selected is MediaType.IMAGE_TO_VIDEO


def test_falls_back_when_video_duration_is_unsupported() -> None:
    scene = Scene(
        index=1,
        start_seconds=0,
        duration_seconds=8,
        preferred_media_type=MediaType.IMAGE_TO_VIDEO,
        fallback_media_type=MediaType.IMAGE_MOTION,
    )
    selected = select_media_type(
        scene,
        video=VideoCapability(image_to_video=True, max_duration_seconds=5),
    )
    assert selected is MediaType.IMAGE_MOTION


def test_memory_gate_falls_back_to_static_motion() -> None:
    scene = Scene(
        index=1,
        start_seconds=0,
        duration_seconds=4,
        preferred_media_type=MediaType.IMAGE_TO_VIDEO,
        fallback_media_type=MediaType.STATIC_IMAGE,
    )
    selected = select_media_type(
        scene,
        video=VideoCapability(
            image_to_video=True,
            max_duration_seconds=5,
            memory_class="high",
        ),
        available_memory_gb=4,
    )
    assert selected is MediaType.STATIC_IMAGE


def test_text_to_video_is_used_only_when_supported() -> None:
    scene = Scene(
        index=1,
        start_seconds=0,
        duration_seconds=4,
        preferred_media_type=MediaType.TEXT_TO_VIDEO,
        fallback_media_type=MediaType.STATIC_IMAGE,
    )
    selected = select_media_type(scene, video=VideoCapability(text_to_video=True))
    assert selected is MediaType.TEXT_TO_VIDEO
