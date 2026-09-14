"""Unit coverage for deterministic Phase 9 media QA boundaries."""

from pathlib import Path

import pytest

from app.exceptions import VideoAgentError
from app.qa.media import validate_image


def _png(width: int, height: int) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + (13).to_bytes(4, "big")
        + b"IHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x02\x00\x00\x00"
    )


def test_validate_image_reads_png_dimensions_and_hash(tmp_path: Path) -> None:
    image = tmp_path / "scene.png"
    image.write_bytes(_png(1024, 576))

    result = validate_image(image, expected_width=1024, expected_height=576)

    assert result["width"] == 1024
    assert result["height"] == 576
    assert isinstance(result["sha256"], str)


def test_validate_image_rejects_invalid_signature(tmp_path: Path) -> None:
    image = tmp_path / "scene.png"
    image.write_bytes(b"not-a-png")

    with pytest.raises(VideoAgentError, match="valid PNG"):
        validate_image(image)
