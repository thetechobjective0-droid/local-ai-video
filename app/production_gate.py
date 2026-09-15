"""Deterministic V1 production-gate evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable
from uuid import UUID

from app.evaluation import evaluate_project
from app.models.project import VideoProject
from app.qa.project import validate_project
from app.security import audit_tree, local_only_findings
from app.storage.filesystem import FilesystemStore


@dataclass(frozen=True)
class GateCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ProductionGateReport:
    passed: bool
    checks: tuple[GateCheck, ...]
    gate_version: str = "1.0"

    def to_dict(self) -> dict[str, object]:
        return {
            "gate_version": self.gate_version,
            "passed": self.passed,
            "checks": [asdict(check) for check in self.checks],
        }


def run_production_gate(
    store: FilesystemStore,
    project_id: UUID,
    *,
    command_available: Callable[[str], bool] | None = None,
) -> ProductionGateReport:
    """Require locality, storage security, deterministic QA and semantic baseline pass."""
    checks: list[GateCheck] = []
    project = store.load_project(project_id)
    checks.append(GateCheck("schema", project.schema_version == "1.1", project.schema_version))
    checks.extend(
        GateCheck(finding.name, finding.passed, finding.detail)
        for finding in local_only_findings(
            "http://127.0.0.1:11434", "http://localhost:11434"
        )
    )
    checks.extend(
        GateCheck(finding.name, finding.passed, finding.detail)
        for finding in audit_tree(store.project_dir(project_id))
    )
    qa = validate_project(store, project_id)
    checks.append(
        GateCheck("deterministic_qa", qa.passed, "QA PASS" if qa.passed else "; ".join(f.message for f in qa.failures))
    )
    evaluation = evaluate_project(store, project_id)
    checks.append(
        GateCheck(
            "semantic_baseline",
            evaluation.passed,
            "semantic baseline PASS" if evaluation.passed else "semantic baseline below threshold",
        )
    )
    return ProductionGateReport(passed=all(check.passed for check in checks), checks=tuple(checks))


def write_gate_report(report: ProductionGateReport, path: Path) -> Path:
    """Persist a production-gate report."""
    import json

    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path
