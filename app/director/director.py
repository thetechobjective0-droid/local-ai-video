"""Director generation stages."""

import json

from app.director.brief import CreativeBrief
from app.director.prompts import PROMPT_VERSION, load_prompt
from app.director.schemas import Script, Storyboard, validate_storyboard_duration
from app.director.structured import generate_validated
from app.providers.base import LLMProvider, LLMRequest

DIRECTOR_PROMPT_VERSION = PROMPT_VERSION


def _request(prompt: str, *, system: str | None = None, model: str | None = None,
             temperature: float = 0.2, top_p: float = 0.9, top_k: int = 40) -> LLMRequest:
    return LLMRequest(
        system=system or load_prompt("system.txt"),
        prompt=prompt,
        model=model,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
    )


def build_brief(provider: LLMProvider, user_prompt: str, duration_seconds: float,
                style: str, *, model: str | None = None, temperature: float = 0.2,
                top_p: float = 0.9, top_k: int = 40) -> CreativeBrief:
    request = _request(
        load_prompt("brief.txt").format(
            user_prompt=user_prompt,
            duration_seconds=duration_seconds,
            style=style,
        ), model=model, temperature=temperature, top_p=top_p, top_k=top_k,
    )
    return generate_validated(provider, request, CreativeBrief)


def build_script(provider: LLMProvider, brief: CreativeBrief, *, model: str | None = None,
                 temperature: float = 0.2, top_p: float = 0.9, top_k: int = 40) -> Script:
    request = _request(
        load_prompt("script.txt").format(
            brief=json.dumps(brief.model_dump(mode="json"), ensure_ascii=False)
        ), model=model, temperature=temperature, top_p=top_p, top_k=top_k,
    )
    return generate_validated(provider, request, Script)


def build_storyboard(provider: LLMProvider, brief: CreativeBrief, script: Script, *,
                     model: str | None = None, temperature: float = 0.2,
                     top_p: float = 0.9, top_k: int = 40) -> Storyboard:
    request = _request(
        load_prompt("storyboard.txt").format(
            brief=json.dumps(brief.model_dump(mode="json"), ensure_ascii=False),
            script=json.dumps(script.model_dump(mode="json"), ensure_ascii=False),
            duration_seconds=brief.duration_seconds,
        ), model=model, temperature=temperature, top_p=top_p, top_k=top_k,
    )
    storyboard = generate_validated(provider, request, Storyboard)
    validate_storyboard_duration(storyboard, brief.duration_seconds)
    return storyboard
