"""Command-line entry point."""

from pathlib import Path

import typer

from app.config import load_config
from app.director.project import create_plan, resume_plan
from app.health import CheckResult, run_health_checks
from app.logging import configure_logging
from app.providers.ollama import OllamaProvider
from app.storage.filesystem import FilesystemStore

app = typer.Typer(help="Local-only AI video generation agent.")


def _checks(config_path: Path | None) -> list[CheckResult]:
    configure_logging()
    return run_health_checks(load_config(config_path))


def _provider_and_store(config_path: Path | None) -> tuple[OllamaProvider, FilesystemStore]:
    app_config = load_config(config_path)
    configure_logging()
    if not app_config.runtime.local_only:
        raise typer.BadParameter("local_only must remain enabled")
    if app_config.llm.provider != "ollama":
        raise typer.BadParameter("only the local Ollama provider is supported in Phase 1")
    provider = OllamaProvider(app_config.llm.base_url)
    provider.require_health()
    return provider, FilesystemStore(app_config.storage.root)


@app.command()
def health(config: Path | None = typer.Option(None, "--config", exists=True)) -> None:
    """Run lightweight environment health checks."""
    results = _checks(config)
    for result in results:
        typer.echo(f"{result.name}: {result.detail}")
    if any(not result.ok for result in results):
        raise typer.Exit(code=1)


@app.command()
def doctor(config: Path | None = typer.Option(None, "--config", exists=True)) -> None:
    """Run detailed local environment checks."""
    results = _checks(config)
    for result in results:
        status = "OK" if result.ok else "FAIL"
        typer.echo(f"[{status}] {result.name}: {result.detail}")
    if any(not result.ok for result in results):
        raise typer.Exit(code=1)


@app.command()
def create(
    prompt: str,
    duration: float = typer.Option(60.0, "--duration", min=0.1),
    style: str = typer.Option("cinematic", "--style"),
    aspect_ratio: str = typer.Option("16:9", "--aspect-ratio"),
    config: Path | None = typer.Option(None, "--config", exists=True),
) -> None:
    """Create a validated local Director plan from a natural-language prompt."""
    app_config = load_config(config)
    provider, store = _provider_and_store(config)
    directory = create_plan(
        provider, store, prompt, duration, style, aspect_ratio,
        model=app_config.llm.model,
        temperature=app_config.llm.temperature,
        top_p=app_config.llm.top_p,
        top_k=app_config.llm.top_k,
        quality_profile=app_config.runtime.profile,
    )
    typer.echo(f"Created project: {directory}")


@app.command()
def resume(
    project_id: str,
    config: Path | None = typer.Option(None, "--config", exists=True),
) -> None:
    """Resume the first incomplete or invalid Director stage."""
    app_config = load_config(config)
    provider, store = _provider_and_store(config)
    directory = resume_plan(
        provider, store, project_id,
        model=app_config.llm.model,
        temperature=app_config.llm.temperature,
        top_p=app_config.llm.top_p,
        top_k=app_config.llm.top_k,
    )
    typer.echo(f"Resumed project: {directory}")
