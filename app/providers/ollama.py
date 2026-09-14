"""Local Ollama LLM adapter."""

import json
import logging
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.exceptions import ProviderUnavailableError, VideoAgentError
from app.providers.base import LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


class OllamaProvider:
    """Call only an Ollama server bound to an approved local hostname."""

    ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

    def __init__(self, base_url: str = "http://127.0.0.1:11434") -> None:
        parsed = urlparse(base_url)
        if parsed.scheme != "http" or parsed.hostname not in self.ALLOWED_HOSTS:
            raise ValueError("Ollama provider must use an HTTP localhost endpoint")
        if parsed.username or parsed.password:
            raise ValueError("Ollama endpoint must not contain credentials")
        self.base_url = base_url.rstrip("/")
        logger.info("[ollama] provider initialized endpoint=%s", self.base_url)

    def health(self, timeout_seconds: float = 2.0) -> tuple[bool, str]:
        """Return availability and a concise diagnostic message."""
        logger.info("[ollama] health check START endpoint=%s", self.base_url)
        request = Request(f"{self.base_url}/api/tags", method="GET")
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            logger.warning("[ollama] health check FAILED error=%s", exc)
            return False, f"unreachable: {exc}"

        models = payload.get("models", [])
        detail = f"reachable; {len(models)} local model(s) reported"
        logger.info("[ollama] health check OK %s", detail)
        return True, detail

    def require_health(self) -> None:
        """Raise a typed error when the local Ollama service is unavailable."""
        ok, detail = self.health()
        if not ok:
            raise ProviderUnavailableError(f"Ollama unavailable: {detail}")

    def models(self, timeout_seconds: float = 5.0) -> list[str]:
        """Return model names advertised by the local Ollama service."""
        logger.info("[ollama] model listing START")
        request = Request(f"{self.base_url}/api/tags", method="GET")
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, TimeoutError) as exc:
            logger.warning("[ollama] model listing FAILED error=%s", exc)
            raise ProviderUnavailableError(f"Ollama model listing failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            logger.warning("[ollama] model listing returned invalid JSON")
            raise VideoAgentError("Ollama returned invalid model-list JSON") from exc

        raw_models = payload.get("models", [])
        if not isinstance(raw_models, list):
            raise VideoAgentError("Ollama model list had an invalid shape")
        names: list[str] = []
        for entry in raw_models:
            if isinstance(entry, dict) and isinstance(entry.get("name"), str):
                names.append(entry["name"])
        logger.info("[ollama] model listing COMPLETE count=%s models=%s", len(names), ", ".join(names))
        return names

    def require_model(self, model: str) -> None:
        """Fail before generation when the configured model is not installed locally."""
        if not model.strip():
            raise ValueError("Ollama model name must not be empty")
        logger.info("[ollama] checking configured model=%s", model)
        installed = self.models()
        if model not in installed:
            logger.error("[ollama] configured model unavailable model=%s", model)
            raise ProviderUnavailableError(
                f"Ollama model '{model}' is not installed locally; installed models: {', '.join(installed) or 'none'}"
            )
        logger.info("[ollama] configured model available model=%s", model)

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate text through Ollama's local chat endpoint."""
        model = request.model or "qwen2.5-coder:32b"
        logger.info(
            "[ollama] generation START model=%s format=%s temperature=%s top_p=%s top_k=%s prompt_chars=%s",
            model, request.format or "default", request.temperature, request.top_p, request.top_k, len(request.prompt),
        )
        messages: list[dict[str, str]] = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "format": request.format,
            "options": {"temperature": request.temperature, "top_p": request.top_p, "top_k": request.top_k},
        }
        body = json.dumps(payload).encode("utf-8")
        http_request = Request(f"{self.base_url}/api/chat", data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(http_request, timeout=300) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, TimeoutError) as exc:
            logger.exception("[ollama] generation FAILED model=%s error=%s", model, exc)
            raise ProviderUnavailableError(f"Ollama generation failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            logger.exception("[ollama] generation returned invalid response JSON model=%s", model)
            raise VideoAgentError("Ollama returned invalid JSON") from exc

        message = result.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise VideoAgentError("Ollama response did not contain message.content")
        metadata = {
            "total_duration_ns": result.get("total_duration"),
            "prompt_eval_count": result.get("prompt_eval_count"),
            "eval_count": result.get("eval_count"),
        }
        logger.info(
            "[ollama] generation COMPLETE model=%s response_chars=%s duration_ns=%s prompt_tokens=%s eval_tokens=%s",
            result.get("model", model), len(message["content"]), metadata["total_duration_ns"],
            metadata["prompt_eval_count"], metadata["eval_count"],
        )
        return LLMResponse(text=message["content"], model=str(result.get("model", model)), metadata=metadata)
