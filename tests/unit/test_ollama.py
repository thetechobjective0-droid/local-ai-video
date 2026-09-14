from unittest.mock import patch

from app.providers.ollama import OllamaProvider


def test_ollama_health_reports_models() -> None:
    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"models": [{"name": "qwen"}]}'

    with patch("app.providers.ollama.urlopen", return_value=Response()):
        ok, detail = OllamaProvider().health()

    assert ok is True
    assert "1 local model" in detail


def test_ollama_health_reports_unreachable() -> None:
    with patch("app.providers.ollama.urlopen", side_effect=OSError("connection refused")):
        ok, detail = OllamaProvider().health()

    assert ok is False
    assert "unreachable" in detail
