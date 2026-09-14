"""Bounded structured-output repair for local LLM responses."""

import json
import logging
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.providers.base import LLMProvider, LLMRequest

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(ValueError):
    """Raised when model output cannot be repaired into the requested schema."""


def parse_json(text: str, model: type[T]) -> T:
    """Parse JSON and validate it against a Pydantic model."""
    logger.info("[structured] parsing model=%s response_chars=%s", model.__name__, len(text))
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("[structured] invalid JSON model=%s error=%s", model.__name__, exc)
        raise StructuredOutputError(f"model output was not valid JSON: {exc}") from exc
    try:
        result = model.model_validate(data)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        logger.warning("[structured] schema validation failed model=%s details=%s", model.__name__, details)
        raise StructuredOutputError(f"model JSON failed schema validation: {details}") from exc
    logger.info("[structured] schema validation passed model=%s", model.__name__)
    return result


def generate_validated(provider: LLMProvider, request: LLMRequest, model: type[T], repair_attempts: int = 2) -> T:
    """Generate structured output and retry only bounded validation failures."""
    if repair_attempts < 0:
        raise ValueError("repair_attempts must be non-negative")
    logger.info("[structured] generation START model=%s repair_attempts=%s", model.__name__, repair_attempts)
    response = provider.generate(request)
    logger.info("[structured] initial response received model=%s", model.__name__)
    try:
        result = parse_json(response.text, model)
        logger.info("[structured] generation COMPLETE model=%s attempt=initial", model.__name__)
        return result
    except StructuredOutputError as original_error:
        last_error: Exception = original_error
        logger.warning("[structured] initial validation failed model=%s error=%s", model.__name__, original_error)

    for attempt in range(1, repair_attempts + 1):
        logger.info("[structured] repair START model=%s attempt=%s/%s", model.__name__, attempt, repair_attempts)
        repair_request = LLMRequest(
            system=(
                "Repair the supplied model output. Return ONLY valid JSON matching "
                "the requested schema. Do not add commentary or executable code."
            ),
            prompt=(
                f"Schema: {model.model_json_schema()}\n"
                f"Invalid output: {response.text}\n"
                f"Previous validation error: {last_error}"
            ),
            model=request.model,
            temperature=0,
            top_p=1,
            top_k=request.top_k,
            format="json",
        )
        response = provider.generate(repair_request)
        logger.info("[structured] repair response received model=%s attempt=%s/%s", model.__name__, attempt, repair_attempts)
        try:
            result = parse_json(response.text, model)
            logger.info("[structured] generation COMPLETE model=%s attempt=repair-%s", model.__name__, attempt)
            return result
        except StructuredOutputError as exc:
            last_error = exc
            logger.warning("[structured] repair validation failed model=%s attempt=%s/%s error=%s", model.__name__, attempt, repair_attempts, exc)

    raise StructuredOutputError(
        f"structured output remained invalid after {repair_attempts} repair attempt(s): {last_error}"
    ) from last_error
