from unittest.mock import patch

import pytest

from app.exceptions import ProviderUnavailableError
from app.providers.ollama import OllamaProvider


class Response:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def test_ollama_health_reports_models() -> None:
    with patch(
        "app.providers.ollama.urlopen",
        return_value=Response(b'{"models": [{"name": "qwen"}]}'),
    ):
        ok, detail = OllamaProvider().health()

    assert ok is True
    assert "1 local model" in detail


def test_ollama_health_reports_unreachable() -> None:
    with patch("app.providers.ollama.urlopen", side_effect=OSError("connection refused")):
        ok, detail = OllamaProvider().health()

    assert ok is False
    assert "unreachable" in detail


def test_ollama_models_returns_installed_names() -> None:
    with patch(
        "app.providers.ollama.urlopen",
        return_value=Response(
            b'{"models": [{"name": "qwen3:4b"}, {"name": "qwen2.5-coder:32b"}]}'
        ),
    ):
        assert OllamaProvider().models() == ["qwen3:4b", "qwen2.5-coder:32b"]


def test_ollama_require_model_rejects_missing_model() -> None:
    with patch(
        "app.providers.ollama.urlopen",
        return_value=Response(b'{"models": [{"name": "qwen3:4b"}]}'),
    ):
        with pytest.raises(ProviderUnavailableError, match="not installed locally"):
            OllamaProvider().require_model("qwen2.5-coder:32b")
