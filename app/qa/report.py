"""Persistence helpers for deterministic project QA reports."""

from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.qa.project import QAReport


def write_qa_report(path: Path, report: "QAReport") -> None:
    """Persist a machine-readable QA report atomically."""
    import json

    payload = {
        "schema_version": "1.0",
        "passed": report.passed,
        "failures": [asdict(failure) for failure in report.failures],
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
