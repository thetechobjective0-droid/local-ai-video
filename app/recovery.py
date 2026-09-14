"""Bounded recovery primitives for local generation workflows."""

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RecoveryPolicy:
    """Explicit retry limits for one recovery domain."""

    max_attempts: int
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,)

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")


@dataclass(frozen=True)
class RecoveryResult(Generic[T]):
    """Result and attempt count from a bounded operation."""

    value: T
    attempts: int


def run_bounded(operation: Callable[[int], T], policy: RecoveryPolicy) -> RecoveryResult[T]:
    """Run an operation with an explicit finite retry budget."""
    last_error: Exception | None = None
    for attempt in range(policy.max_attempts):
        try:
            return RecoveryResult(value=operation(attempt), attempts=attempt + 1)
        except policy.retryable_exceptions as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


LLM_REPAIR_POLICY = RecoveryPolicy(max_attempts=3)
IMAGE_RETRY_POLICY = RecoveryPolicy(max_attempts=3)
VIDEO_RETRY_POLICY = RecoveryPolicy(max_attempts=3)
RENDER_RETRY_POLICY = RecoveryPolicy(max_attempts=2)
