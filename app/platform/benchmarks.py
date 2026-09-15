"""Local machine-readable benchmark and performance reports."""

from __future__ import annotations

import json
import platform
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from uuid import UUID, uuid4

from app.preflight import snapshot
from app.storage.filesystem import FilesystemStore


@dataclass(frozen=True)
class BenchmarkMeasurement:
    name: str
    value: float
    unit: str


@dataclass(frozen=True)
class BenchmarkReport:
    id: UUID
    created_at_ns: int
    machine: str
    measurements: tuple[BenchmarkMeasurement, ...] = field(default_factory=tuple)
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "created_at_ns": self.created_at_ns,
            "machine": self.machine,
            "measurements": [asdict(value) for value in self.measurements],
            "metadata": self.metadata,
        }


def collect_environment_report(
    store: FilesystemStore, project_id: UUID | None = None
) -> BenchmarkReport:
    """Capture reproducible local environment measurements without network access."""
    start = time.perf_counter_ns()
    resources = snapshot(store.root)
    measurements = (
        BenchmarkMeasurement("total_memory", float(resources.total_memory_bytes), "bytes"),
        BenchmarkMeasurement("available_memory", float(resources.available_memory_bytes), "bytes"),
        BenchmarkMeasurement("free_disk", float(resources.free_disk_bytes), "bytes"),
        BenchmarkMeasurement("collector_overhead", float(time.perf_counter_ns() - start), "ns"),
    )
    report = BenchmarkReport(
        id=uuid4(),
        created_at_ns=time.time_ns(),
        machine=platform.platform(),
        measurements=measurements,
        metadata={
            "project_id": str(project_id) if project_id else None,
            "python": platform.python_version(),
        },
    )
    path = store.root / "benchmarks"
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{report.id}.json").write_text(
        json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    return report


def list_benchmark_reports(root: Path) -> list[dict[str, object]]:
    """Read valid benchmark records, newest first."""
    directory = root.expanduser().resolve() / "benchmarks"
    reports: list[dict[str, object]] = []
    for path in sorted(directory.glob("*.json"), reverse=True) if directory.exists() else []:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            continue
        if isinstance(value, dict):
            reports.append(value)
    return reports


def compare_reports(
    baseline: dict[str, object], candidate: dict[str, object]
) -> dict[str, object]:
    """Compare shared measurements and surface percentage deltas."""
    baseline_measurements = _measurements(baseline)
    candidate_measurements = _measurements(candidate)
    comparisons: list[dict[str, object]] = []
    for name in sorted(set(baseline_measurements) & set(candidate_measurements)):
        base = baseline_measurements[name]
        current = candidate_measurements[name]
        delta = current - base
        comparisons.append(
            {
                "name": name,
                "baseline": base,
                "candidate": current,
                "delta": delta,
                "percent_delta": (delta / base * 100.0) if base else None,
            }
        )
    return {
        "baseline_id": baseline.get("id"),
        "candidate_id": candidate.get("id"),
        "comparisons": comparisons,
    }


def _measurements(report: dict[str, object]) -> dict[str, float]:
    raw = report.get("measurements")
    if not isinstance(raw, list):
        return {}
    result: dict[str, float] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        value = item.get("value")
        if isinstance(name, str) and isinstance(value, (int, float)):
            result[name] = float(value)
    return result
