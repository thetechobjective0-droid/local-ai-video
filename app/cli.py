"""Command-line entry point."""

from pathlib import Path

import typer

from app.config import load_config
from app.health import run_health_checks
from app.logging import configure_logging

app = typer.Typer(help="Local-only AI video generation agent.")


def _checks(config_path: Path | None) -> list:
    configure_logging()
    return run_health_checks(load_config(config_path))


@app.command()
def health(config: Path | None = typer.Option(None, "--config", exists=True)) -> None:
    """Run local dependency and resource checks."""
    for result in _checks(config):
        status = "OK" if result.ok else "MISSING"
        typer.echo(f"[{status}] {result.name}: {result.detail}")


@app.command()
def doctor(config: Path | None = typer.Option(None, "--config", exists=True)) -> None:
    """Run the Phase 0 local environment doctor and fail on any missing dependency."""
    results = _checks(config)
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        typer.echo(f"[{status}] {result.name}: {result.detail}")
    if not all(result.ok for result in results):
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
