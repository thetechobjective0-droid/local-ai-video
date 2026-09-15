"""In-process observability without network telemetry."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from time import monotonic
from typing import Any


@dataclass
class PipelineMetrics:
    """Bounded metrics for one local pipeline execution."""

    counters: dict[str, int] = field(default_factory=dict)
    durations_seconds: dict[str, list[float]] = field(default_factory=dict)

    def increment(self, name: str, amount: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + amount

    def observe(self, name: str, seconds: float) -> None:
        self.durations_seconds.setdefault(name, []).append(max(0.0, seconds))

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
