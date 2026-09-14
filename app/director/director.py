"""Director generation stages."""

import json
import logging

from app.director.brief import CreativeBrief
from app.director.prompts import PROMPT_VERSION, load_prompt
from app.director.schemas import (
    Script,
    Storyboard,
    validate_script_duration,
    validate_storyboard_duration,
)
from app.director.structured import generate_validated
from app.providers.base import LLMProvider, LLMRequest

logger = logging.getLogger(__name__)
DIRECTOR_PROMPT_VERSION = PROMPT_VERSION


def _request(
    prompt: str,
    *,
    system: str | None = None,
    model: str | None = None,
    temperature: float = 0.2,
    top_p: float = 0.9,
    top_k: int = 40,
) -> LLMRequest:
    return LLMRequest(
        system=system or load_prompt("system.txt"),
        prompt=prompt,
        model=model,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
    )


def build_brief(
    provider: LLMProvider,
    user_prompt: str,
    duration_seconds: float,
    style: str,
    *,
    model: str | None = None,
    temperature: float = 0.2,
    top_p: float = 0.9,
    top_k: int = 40,
) -> CreativeBrief:
    logger.info(
        "[llm] brief request model=%s prompt_chars=%s duration=%ss style=%s",
        model or "default",
        len(user_prompt),
        duration_seconds,
        style,
    )
    request = _request(
        load_prompt("brief.txt").format(
            user_prompt=user_prompt, duration_seconds=duration_seconds, style=style
        ),
        model=model,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
    )
    result = generate_validated(provider, request, CreativeBrief)
    logger.info(
        "[llm] brief validated title=%r language=%s audience=%r",
        result.title,
        result.language,
        result.audience,
    )
    return result


def build_script(
    provider: LLMProvider,
    brief: CreativeBrief,
    *,
    model: str | None = None,
    temperature: float = 0.2,
    top_p: float = 0.9,
    top_k: int = 40,
) -> Script:
    logger.info(
        "[llm] script request model=%s brief_duration=%ss",
        model or "default",
        brief.duration_seconds,
    )
    request = _request(
        load_prompt("script.txt").format(
            brief=json.dumps(brief.model_dump(mode="json"), ensure_ascii=False)
        ),
        model=model,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
    )
    script = generate_validated(provider, request, Script)
    logger.info(
        "[llm] script JSON validated; validating duration against %ss", brief.duration_seconds
    )
    validate_script_duration(script, brief.duration_seconds)
    logger.info("[llm] script validated duration_estimate=%ss", script.estimated_duration_seconds)
    return script


def build_storyboard(
    provider: LLMProvider,
    brief: CreativeBrief,
    script: Script,
    *,
    model: str | None = None,
    temperature: float = 0.2,
    top_p: float = 0.9,
    top_k: int = 40,
) -> Storyboard:
    logger.info(
        "[llm] storyboard request model=%s target_duration=%ss",
        model or "default",
        brief.duration_seconds,
    )
    request = _request(
        load_prompt("storyboard.txt").format(
            brief=json.dumps(brief.model_dump(mode="json"), ensure_ascii=False),
            script=json.dumps(script.model_dump(mode="json"), ensure_ascii=False),
            duration_seconds=brief.duration_seconds,
        ),
        model=model,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
    )
    storyboard = generate_validated(provider, request, Storyboard)
    logger.info(
        "[llm] storyboard JSON validated; validating timing scenes=%s", len(storyboard.scenes)
    )
    validate_storyboard_duration(storyboard, brief.duration_seconds)
    logger.info(
        "[llm] storyboard validated scenes=%s target_duration=%ss",
        len(storyboard.scenes),
        brief.duration_seconds,
    )
    return storyboard
