"""Minimal local Ollama health adapter."""

import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.exceptions import ProviderUnavailableError


class OllamaProvider:
    """Probe an Ollama server without performing inference."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434") -> None:
        self.base_url = base_url.rstrip("/")

    def health(self, timeout_seconds: float = 2.0) -> tuple[bool, str]:
        """Return availability and a concise diagnostic message."""
        request = Request(f"{self.base_url}/api/tags", method="GET")
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            return False, f"unreachable: {exc}"

        models = payload.get("models", [])
        return True, f"reachable; {len(models)} local model(s) reported"

    def require_health(self) -> None:
        """Raise a typed error when the local Ollama service is unavailable."""
        ok, detail = self.health()
        if not ok:
            raise ProviderUnavailableError(f"Ollama unavailable: {detail}")
