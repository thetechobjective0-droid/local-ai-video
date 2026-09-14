"""Command-line entry point."""

from pathlib import Path

import typer

from app.config import load_config
from app.director.project import create_plan
from app.health import CheckResult, run_health_checks
from app.logging import configure_logging
from app.providers.ollama import OllamaProvider
from app.storage.filesystem import FilesystemStore

app = typer.Typer(help="Local-only AI video generation agent.")


def _checks(config_path: Path | None) -> list[CheckResult]:
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


@app.command()
def create(
    prompt: str,
    duration: float = typer.Option(60.0, "--duration", min=0.1),
    style: str = typer.Option("balanced", "--style"),
    aspect_ratio: str = typer.Option("16:9", "--aspect-ratio"),
    config: Path | None = typer.Option(None, "--config", exists=True),
) -> None:
    """Create a validated local Director plan from a natural-language prompt."""
    app_config = load_config(config)
    configure_logging()
    provider = OllamaProvider()
    provider.require_health()
    store = FilesystemStore(app_config.storage.root)
    directory = create_plan(provider, store, prompt, duration, style, aspect_ratio)
    typer.echo(f"Created project: {directory}")


if __name__ == "__main__":
    app()
