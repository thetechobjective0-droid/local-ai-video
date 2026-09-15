"""In-process observability without network telemetry."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from time import monotonic
from typing import Any


_MAX_COUNTERS = 128
_MAX_DURATION_NAMES = 128
_MAX_DURATION_SAMPLES = 128


@dataclass
class PipelineMetrics:
    """Bounded metrics for one local pipeline execution."""

    counters: dict[str, int] = field(default_factory=dict)
    durations_seconds: dict[str, deque[float]] = field(default_factory=dict)

    def increment(self, name: str, amount: int = 1) -> None:
        if name not in self.counters and len(self.counters) >= _MAX_COUNTERS:
            raise ValueError("metric counter limit exceeded")
        self.counters[name] = self.counters.get(name, 0) + amount

    def observe(self, name: str, seconds: float) -> None:
        if name not in self.durations_seconds and len(self.durations_seconds) >= _MAX_DURATION_NAMES:
            raise ValueError("metric duration-name limit exceeded")
        self.durations_seconds.setdefault(name, deque(maxlen=_MAX_DURATION_SAMPLES)).append(
            max(0.0, seconds)
        )

    def timer(self, name: str) -> "MetricTimer":
        return MetricTimer(self, name)

    def snapshot(self) -> dict[str, Any]:
        return {
            "counters": dict(self.counters),
            "durations_seconds": {
                name: {
                    "count": len(values),
                    "total": sum(values),
                    "min": min(values),
                    "max": max(values),
                    "average": sum(values) / len(values),
                }
                for name, values in self.durations_seconds.items()
                if values
            },
        }


@dataclass
class MetricTimer:
    metrics: PipelineMetrics
    name: str
    started: float = field(default_factory=monotonic)

    def __enter__(self) -> "MetricTimer":
        self.started = monotonic()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.metrics.observe(self.name, monotonic() - self.started)


GLOBAL_METRICS = PipelineMetrics()
