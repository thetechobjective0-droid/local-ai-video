"""Director generation stages."""

import json

from app.director.brief import CreativeBrief
from app.director.schemas import Script, Storyboard
from app.director.structured import generate_validated
from app.providers.base import LLMProvider, LLMRequest

DIRECTOR_SYSTEM = """You are the creative director for a local-only AI video generator.
Return ONLY valid JSON matching the requested schema. Never return executable code,
shell commands, URLs, or instructions to upload data. Keep output concise and production-ready."""


def _request(prompt: str) -> LLMRequest:
    return LLMRequest(system=DIRECTOR_SYSTEM, prompt=prompt)


def build_brief(provider: LLMProvider, user_prompt: str, duration_seconds: float, style: str) -> CreativeBrief:
    """Generate and strictly validate a creative brief."""
    request = _request(
        "Create a creative brief with fields: title, objective, audience, tone, "
        f"language, duration_seconds, visual_style. User idea: {user_prompt!r}. "
        f"Target duration: {duration_seconds}. Style: {style!r}."
    )
    return generate_validated(provider, request, CreativeBrief)


def build_script(provider: LLMProvider, brief: CreativeBrief) -> Script:
    """Generate a validated narration script from the creative brief."""
    request = _request(
        "Create a narration script. Return fields: title, narration, "
        "estimated_duration_seconds. "
        f"Brief: {json.dumps(brief.model_dump(mode='json'))}"
    )
    return generate_validated(provider, request, Script)


def build_storyboard(provider: LLMProvider, brief: CreativeBrief, script: Script) -> Storyboard:
    """Generate and validate a scene-level storyboard."""
    request = _request(
        "Create a storyboard as a JSON object with a scenes array. Each scene must "
        "contain id, index, start_seconds, duration_seconds, narration, "
        "visual_description, image_prompt, and motion_prompt. Use contiguous scene "
        "indexes starting at 1 and non-overlapping timing. "
        f"Brief: {json.dumps(brief.model_dump(mode='json'))}\n"
        f"Script: {json.dumps(script.model_dump(mode='json'))}"
    )
    return generate_validated(provider, request, Storyboard)
