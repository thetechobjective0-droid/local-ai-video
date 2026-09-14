"""Command-line entry point."""

import json
from pathlib import Path
from uuid import UUID

import typer

from app.config import load_config
from app.director.project import create_plan, resume_plan
from app.generation.audio import generate_scene_audio
from app.generation.images import generate_scene_image
from app.generation.subtitles import build_subtitles
from app.generation.timeline import build_timeline
from app.health import CheckResult, run_health_checks
from app.logging import configure_logging
from app.models.scene import Scene
from app.providers.diffusers_image import DiffusersImageProvider
from app.providers.macos_tts import MacOSTTSProvider
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
    provider.require_model(app_config.llm.model)
    return provider, FilesystemStore(app_config.storage.root)


def _image_provider_and_store(config_path: Path | None) -> tuple[DiffusersImageProvider, FilesystemStore]:
    app_config = load_config(config_path)
    configure_logging()
    if not app_config.runtime.local_only:
        raise typer.BadParameter("local_only must remain enabled")
    if app_config.image.provider != "diffusers":
        raise typer.BadParameter("only the local Diffusers image provider is supported in Phase 3")
    provider = DiffusersImageProvider(app_config.image.model_path, device=app_config.image.device)
    return provider, FilesystemStore(app_config.storage.root)


def _tts_provider_and_store(config_path: Path | None) -> tuple[MacOSTTSProvider, FilesystemStore]:
    app_config = load_config(config_path)
    configure_logging()
    if not app_config.runtime.local_only:
        raise typer.BadParameter("local_only must remain enabled")
    if app_config.tts.provider != "macos_say":
        raise typer.BadParameter("only the local macOS Speech provider is supported in Phase 4")
    provider = MacOSTTSProvider(sample_rate=app_config.tts.sample_rate)
    return provider, FilesystemStore(app_config.storage.root)


def _load_scene(store: FilesystemStore, project_id: UUID, scene_id: UUID) -> Scene:
    directory = store.project_dir(project_id)
    for path in sorted(directory.glob("scene-*.json")):
        if path.name.endswith(("-image.json", "-audio.json")):
            continue
        try:
            scene = Scene.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if scene.id == scene_id:
            return scene
    raise typer.BadParameter(f"scene not found: {scene_id}")


def _load_scenes(store: FilesystemStore, project_id: UUID) -> list[Scene]:
    directory = store.project_dir(project_id)
    scenes: list[Scene] = []
    for path in sorted(directory.glob("scene-*.json")):
        if path.name.endswith(("-image.json", "-audio.json")):
            continue
        try:
            scenes.append(Scene.model_validate_json(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    if not scenes:
        raise typer.BadParameter(f"no scenes found: {project_id}")
    return scenes


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
        provider,
        store,
        prompt,
        duration,
        style,
        aspect_ratio,
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
        provider,
        store,
        project_id,
        model=app_config.llm.model,
        temperature=app_config.llm.temperature,
        top_p=app_config.llm.top_p,
        top_k=app_config.llm.top_k,
    )
    typer.echo(f"Resumed project: {directory}")


@app.command("generate-scene")
def generate_scene(
    project_id: str,
    scene_id: str,
    seed: int | None = typer.Option(None, "--seed"),
    config: Path | None = typer.Option(None, "--config", exists=True),
) -> None:
    """Generate one scene image using the configured local image provider."""
    app_config = load_config(config)
    provider, store = _image_provider_and_store(config)
    project_uuid = UUID(project_id)
    scene = _load_scene(store, project_uuid, UUID(scene_id))
    artifact, _ = generate_scene_image(
        provider,
        store,
        project_uuid,
        scene,
        model=app_config.image.model_path.name,
        width=app_config.image.width,
        height=app_config.image.height,
        steps=app_config.image.steps,
        guidance_scale=app_config.image.guidance_scale,
        seed=seed,
    )
    typer.echo(f"Generated image artifact: {artifact.id}")


@app.command("generate-audio")
def generate_audio(
    project_id: str,
    scene_id: str,
    config: Path | None = typer.Option(None, "--config", exists=True),
) -> None:
    """Generate one scene narration track using local macOS Speech."""
    app_config = load_config(config)
    provider, store = _tts_provider_and_store(config)
    project_uuid = UUID(project_id)
    scene = _load_scene(store, project_uuid, UUID(scene_id))
    artifact, _ = generate_scene_audio(
        provider,
        store,
        project_uuid,
        scene,
        voice=app_config.tts.voice,
        rate=app_config.tts.rate,
    )
    typer.echo(f"Generated audio artifact: {artifact.id}")


@app.command("subtitles")
def subtitles(
    project_id: str,
    max_chars: int = typer.Option(48, "--max-chars", min=1),
    config: Path | None = typer.Option(None, "--config", exists=True),
) -> None:
    """Generate deterministic SRT and WebVTT subtitles for a project."""
    store = FilesystemStore(load_config(config).storage.root)
    project_uuid = UUID(project_id)
    outputs = build_subtitles(store, project_uuid, _load_scenes(store, project_uuid), max_chars=max_chars)
    for format_name, path in outputs.items():
        typer.echo(f"Generated {format_name}: {path}")


@app.command("timeline")
def timeline(
    project_id: str,
    config: Path | None = typer.Option(None, "--config", exists=True),
) -> None:
    """Build and persist the deterministic timeline manifest."""
    store = FilesystemStore(load_config(config).storage.root)
    project_uuid = UUID(project_id)
    project = store.load_project(project_uuid)
    result = build_timeline(store, project, _load_scenes(store, project_uuid))
    typer.echo(f"Generated timeline: {store.project_dir(project_uuid) / 'timeline.json'}")
    typer.echo(f"Scenes: {len(result.scenes)}")


if __name__ == "__main__":
    app()
