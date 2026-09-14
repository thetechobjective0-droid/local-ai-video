"""Bounded structured-output repair for local LLM responses."""

import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.providers.base import LLMProvider, LLMRequest

T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(ValueError):
    """Raised when model output cannot be repaired into the requested schema."""


def parse_json(text: str, model: type[T]) -> T:
    """Parse JSON and validate it against a Pydantic model."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StructuredOutputError("model output was not valid JSON") from exc
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        raise StructuredOutputError(
            f"model JSON failed schema validation: {details}"
        ) from exc


def generate_validated(
    provider: LLMProvider,
    request: LLMRequest,
    model: type[T],
    repair_attempts: int = 2,
) -> T:
    """Generate structured output and retry only bounded validation failures."""
    if repair_attempts < 0:
        raise ValueError("repair_attempts must be non-negative")

    response = provider.generate(request)
    try:
        return parse_json(response.text, model)
    except StructuredOutputError as original_error:
        last_error: Exception = original_error

    for _ in range(repair_attempts):
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
        try:
            return parse_json(response.text, model)
        except StructuredOutputError as exc:
            last_error = exc

    raise StructuredOutputError(
        f"structured output remained invalid after {repair_attempts} repair attempt(s): {last_error}"
    ) from last_error
