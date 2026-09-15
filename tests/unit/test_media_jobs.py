"""Regression tests for media-job provider initialization."""

from pathlib import Path
from uuid import uuid4

from app.config import AppConfig
from app.models.scene import Scene
from app.orchestrator import jobs


def _scene(*, has_image: bool) -> Scene:
    return Scene(
        index=1,
        start_seconds=0,
        duration_seconds=3,
        image_asset=uuid4() if has_image else None,
    )


def test_image_provider_is_not_initialized_when_assets_exist(monkeypatch) -> None:
    config = AppConfig()

    def fail_if_initialized(*args, **kwargs):
        raise AssertionError("Diffusers must not initialize for existing image assets")

    monkeypatch.setattr(jobs, "DiffusersImageProvider", fail_if_initialized)

    assert jobs._build_image_provider_if_needed(config, [_scene(has_image=True)]) is None


def test_image_provider_is_initialized_when_an_asset_is_missing(
    monkeypatch, tmp_path: Path
) -> None:
    config = AppConfig()
    expected = object()

    def fake_provider(model_path, *, device):
        assert model_path == config.image.model_path
        assert device == config.image.device
        return expected

    monkeypatch.setattr(jobs, "DiffusersImageProvider", fake_provider)

    assert jobs._build_image_provider_if_needed(config, [_scene(has_image=False)]) is expected
