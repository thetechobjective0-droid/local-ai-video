"""Local LLM director orchestration."""

import json

from app.director.brief import CreativeBrief
from app.providers.base import LLMProvider, LLMRequest

DIRECTOR_SYSTEM = """You are the creative director for a local-only AI video generator.
Return ONLY valid JSON matching the requested schema. Never return executable code,
shell commands, URLs, or instructions to upload data. Use the user's idea to create
a concise production brief."""


def build_brief(provider: LLMProvider, user_prompt: str, duration_seconds: float, style: str) -> CreativeBrief:
    """Generate and strictly validate a creative brief."""
    request = LLMRequest(
        system=DIRECTOR_SYSTEM,
        prompt=(
            "Create a creative brief with fields: title, objective, audience, tone, "
            f"language, duration_seconds, visual_style. User idea: {user_prompt!r}. "
            f"Target duration: {duration_seconds}. Style: {style!r}."
        ),
    )
    response = provider.generate(request)
    try:
        data = json.loads(response.text)
    except json.JSONDecodeError as exc:
        raise ValueError("Director returned invalid JSON") from exc
    return CreativeBrief.model_validate(data)
