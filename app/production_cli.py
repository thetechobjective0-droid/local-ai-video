"""Operational CLI commands layered onto the main local video-agent CLI."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import typer

from app.cli import app
from app.config import load_config
from app.production_gate import run_production_gate, write_gate_report
from app.storage.filesystem import FilesystemStore
from app.storage.migrations import migrate_storage


@app.command("migrate")
def migrate(
    config: Path | None = typer.Option(None, "--config", exists=True),
) -> None:
    """Upgrade persisted project manifests to the current storage schema."""
    config_data = load_config(config)
    migrated = migrate_storage(config_data.storage.root)
    typer.echo(f"Migrated projects: {migrated}")


@app.command("production-gate")
def production_gate(
    project_id: str,
    report_path: Path | None = typer.Option(
        None, "--report", help="Write the machine-readable gate report to this path."
    ),
    config: Path | None = typer.Option(None, "--config", exists=True),
) -> None:
    """Evaluate one project against the deterministic V1 production gate."""
    config_data = load_config(config)
    store = FilesystemStore(config_data.storage.root)
    project_uuid = UUID(project_id)
    report = run_production_gate(store, project_uuid, config_data)
    output = write_gate_report(
        report, report_path or store.project_dir(project_uuid) / "production-gate.json"
    )
    for check in report.checks:
        typer.echo(f"[{'PASS' if check.passed else 'FAIL'}] {check.name}: {check.detail}")
    typer.echo(f"Report: {output}")
    if not report.passed:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
