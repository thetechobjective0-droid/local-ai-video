"""Command-line entry point for the local video agent."""

import json
from pathlib import Path
from uuid import UUID

import click
import typer

from app.acceptance import run_acceptance, write_report
from app.config import load_config
from app.director.project import create_plan, resume_plan
from app.exceptions import VideoAgentError
from app.generation.audio import generate_scene_audio
from app.generation.image_recovery import generate_scene_image_with_recovery
from app.generation.images import generate_scene_image
from app.generation.subtitles import build_subtitles
from app.generation.timeline import build_timeline
from app.generation.video import generate_scene_video
from app.generation.video_recovery import generate_scene_video_with_recovery
from app.health import CheckResult, run_health_checks
from app.logging import configure_logging
from app.models.scene import Scene
from app.models.timeline import Timeline
from app.orchestrator.media_generation import generate_project_media
from app.providers.capabilities import get_provider_capabilities
from app.providers.diffusers_image import DiffusersImageProvider
from app.providers.factory import build_video_fallback, build_video_provider
from app.providers.macos_tts import MacOSTTSProvider
from app.providers.ollama import OllamaProvider
from app.providers.video import VideoProvider
from app.qa.project import QAReport, validate_project
from app.qa.report import write_qa_report
from app.render.ffmpeg import FFmpegRenderer
from app.storage.filesystem import FilesystemStore

app = typer.Typer(help="Local-only AI video generation agent.")


def _checks(config_path: Path | None) -> list[CheckResult]:
    configure_logging()
    return run_health_checks(load_config(config_path))


def _provider_and_store(config_path: Path | None) -> tuple[OllamaProvider, FilesystemStore]:
    config = load_config(config_path)
    configure_logging()
    if not config.runtime.local_only:
        raise typer.BadParameter("local_only must remain enabled")
    if config.llm.provider != "ollama":
        raise typer.BadParameter("only the local Ollama provider is supported")
    provider = OllamaProvider(config.llm.base_url)
    provider.require_health()
    provider.require_model(config.llm.model)
    return provider, FilesystemStore(config.storage.root)


def _image_provider_and_store(config_path: Path | None) -> tuple[DiffusersImageProvider, FilesystemStore]:
    config = load_config(config_path)
    configure_logging()
    if not config.runtime.local_only:
        raise typer.BadParameter("local_only must remain enabled")
    if config.image.provider != "diffusers":
        raise typer.BadParameter("only the local Diffusers image provider is supported")
    return DiffusersImageProvider(config.image.model_path, device=config.image.device), FilesystemStore(config.storage.root)


def _tts_provider_and_store(config_path: Path | None) -> tuple[MacOSTTSProvider, FilesystemStore]:
    config = load_config(config_path)
    configure_logging()
    if not config.runtime.local_only:
        raise typer.BadParameter("local_only must remain enabled")
    if config.tts.provider != "macos_say":
        raise typer.BadParameter("only the local macOS Speech provider is supported")
    return MacOSTTSProvider(sample_rate=config.tts.sample_rate), FilesystemStore(config.storage.root)


def _video_provider_and_store(config_path: Path | None) -> tuple[VideoProvider, FilesystemStore]:
    config = load_config(config_path)
    configure_logging()
    return build_video_provider(config), FilesystemStore(config.storage.root)


def _load_scenes(store: FilesystemStore, project_id: UUID) -> list[Scene]:
    scenes: list[Scene] = []
    for path in sorted(store.project_dir(project_id).glob("scene-*.json")):
        if path.name.endswith(("-image.json", "-audio.json", "-video.json")):
            continue
        try:
            scenes.append(Scene.model_validate_json(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    if not scenes:
        raise typer.BadParameter(f"no scenes found: {project_id}")
    return scenes


def _load_scene(store: FilesystemStore, project_id: UUID, scene_id: UUID) -> Scene:
    for scene in _load_scenes(store, project_id):
        if scene.id == scene_id:
            return scene
    raise typer.BadParameter(f"scene not found: {scene_id}")


def _write_project_qa(store: FilesystemStore, project_id: UUID, report: QAReport) -> None:
    write_qa_report(store.project_dir(project_id) / "qa-report.json", report)


@app.command()
def health(config: Path | None = typer.Option(None, "--config", exists=True)) -> None:
    """Run lightweight local environment health checks."""
    results = _checks(config)
    for result in results:
        typer.echo(f"{result.name}: {result.detail}")
    if any(not result.ok for result in results):
        raise typer.Exit(code=1)


@app.command()
def doctor(config: Path | None = typer.Option(None, "--config", exists=True)) -> None:
    """Run detailed local environment health checks."""
    results = _checks(config)
    for result in results:
        typer.echo(f"[{'OK' if result.ok else 'FAIL'}] {result.name}: {result.detail}")
    if any(not result.ok for result in results):
        raise typer.Exit(code=1)


@app.command()
def create(prompt: str, duration: float = typer.Option(60.0, "--duration", min=0.1), style: str = typer.Option("cinematic", "--style"), aspect_ratio: str = typer.Option("16:9", "--aspect-ratio"), config: Path | None = typer.Option(None, "--config", exists=True)) -> None:
    """Create a validated local Director plan."""
    config_data = load_config(config)
    provider, store = _provider_and_store(config)
    directory = create_plan(provider, store, prompt, duration, style, aspect_ratio, model=config_data.llm.model, temperature=config_data.llm.temperature, top_p=config_data.llm.top_p, top_k=config_data.llm.top_k, quality_profile=config_data.runtime.profile)
    typer.echo(f"Created project: {directory}")


@app.command()
def resume(project_id: str, config: Path | None = typer.Option(None, "--config", exists=True)) -> None:
    """Resume the first incomplete or invalid Director stage."""
    config_data = load_config(config)
    provider, store = _provider_and_store(config)
    directory = resume_plan(provider, store, project_id, model=config_data.llm.model, temperature=config_data.llm.temperature, top_p=config_data.llm.top_p, top_k=config_data.llm.top_k)
    typer.echo(f"Resumed project: {directory}")


@app.command("generate-scene")
def generate_scene(project_id: str, scene_id: str, seed: int | None = typer.Option(None, "--seed"), config: Path | None = typer.Option(None, "--config", exists=True)) -> None:
    """Generate one local scene image."""
    config_data = load_config(config)
    provider, store = _image_provider_and_store(config)
    scene = _load_scene(store, UUID(project_id), UUID(scene_id))
    artifact, _ = generate_scene_image(provider, store, UUID(project_id), scene, model=config_data.image.model_path.name, width=config_data.image.width, height=config_data.image.height, steps=config_data.image.steps, guidance_scale=config_data.image.guidance_scale, seed=seed)
    typer.echo(f"Generated image artifact: {artifact.id}")


@app.command("generate-audio")
def generate_audio(project_id: str, scene_id: str, config: Path | None = typer.Option(None, "--config", exists=True)) -> None:
    """Generate one local macOS narration track."""
    config_data = load_config(config)
    provider, store = _tts_provider_and_store(config)
    artifact, _ = generate_scene_audio(provider, store, UUID(project_id), _load_scene(store, UUID(project_id), UUID(scene_id)), voice=config_data.tts.voice, rate=config_data.tts.rate)
    typer.echo(f"Generated audio artifact: {artifact.id}")


@app.command("generate-video")
def generate_video(project_id: str, scene_id: str, seed: int | None = typer.Option(None, "--seed"), config: Path | None = typer.Option(None, "--config", exists=True)) -> None:
    """Generate one scene video with the configured local provider."""
    config_data = load_config(config)
    provider, store = _video_provider_and_store(config)
    artifact, _ = generate_scene_video(provider, store, UUID(project_id), _load_scene(store, UUID(project_id), UUID(scene_id)), width=config_data.video.width, height=config_data.video.height, fps=config_data.video.fps, seed=seed)
    typer.echo(f"Generated video artifact: {artifact.id}")


@app.command("generate-media")
def generate_media(project_id: str, config: Path | None = typer.Option(None, "--config", exists=True)) -> None:
    """Generate all project media through deterministic routing and fallback."""
    config_data = load_config(config)
    video_provider, store = _video_provider_and_store(config)
    image_provider, _ = _image_provider_and_store(config)
    results = generate_project_media(store, UUID(project_id), _load_scenes(store, UUID(project_id)), video_provider=video_provider, image_provider=image_provider, image_model=config_data.image.model_path.name, image_width=config_data.image.width, image_height=config_data.image.height, image_steps=config_data.image.steps, image_guidance_scale=config_data.image.guidance_scale, video_capability=get_provider_capabilities(config_data.video.provider).video, fallback_provider=build_video_fallback(config_data), width=config_data.video.width, height=config_data.video.height, fps=config_data.video.fps)
    for result in results:
        suffix = " (fallback)" if result.used_fallback else ""
        typer.echo(f"Scene {result.scene.index}: {result.selected_media_type.value}{suffix}")


@app.command("qa")
def qa(project_id: str, config: Path | None = typer.Option(None, "--config", exists=True)) -> None:
    """Run and persist deterministic project QA."""
    store = FilesystemStore(load_config(config).storage.root)
    report = validate_project(store, UUID(project_id))
    _write_project_qa(store, UUID(project_id), report)
    if not report.passed:
        typer.echo("QA: FAIL")
        for failure in report.failures:
            typer.echo(f"[{failure.scope}] {failure.message}")
        raise typer.Exit(code=1)
    typer.echo("QA: PASS")


@app.command("regenerate-scene")
def regenerate_scene(project_id: str, scene_id: str, stage: str = typer.Option("all", "--stage", click_type=click.Choice(["image", "audio", "video", "all"])), seed: int | None = typer.Option(None, "--seed"), config: Path | None = typer.Option(None, "--config", exists=True)) -> None:
    """Regenerate a selected scene stage using bounded recovery."""
    config_data = load_config(config)
    project_uuid, scene_uuid = UUID(project_id), UUID(scene_id)
    store = FilesystemStore(config_data.storage.root)
    scene = _load_scene(store, project_uuid, scene_uuid)
    directory = store.project_dir(project_uuid)
    if stage in {"image", "all"}:
        (directory / f"scene-{scene.index:04d}-image.json").unlink(missing_ok=True)
        (directory / f"images/scene-{scene.index:04d}.png").unlink(missing_ok=True)
        image_provider, _ = _image_provider_and_store(config)
        image_result = generate_scene_image_with_recovery(image_provider, store, project_uuid, scene, model=config_data.image.model_path.name, width=config_data.image.width, height=config_data.image.height, steps=config_data.image.steps, guidance_scale=config_data.image.guidance_scale, seed=seed)
        scene = image_result.scene
    if stage in {"audio", "all"}:
        audio_provider, _ = _tts_provider_and_store(config)
        _, scene = generate_scene_audio(audio_provider, store, project_uuid, scene, voice=config_data.tts.voice, rate=config_data.tts.rate)
    if stage in {"video", "all"}:
        video_provider, _ = _video_provider_and_store(config)
        try:
            video_result = generate_scene_video_with_recovery(video_provider, store, project_uuid, scene, width=config_data.video.width, height=config_data.video.height, fps=config_data.video.fps, seed=seed)
            scene = video_result.scene
        except VideoAgentError:
            fallback = build_video_fallback(config_data)
            if fallback is None:
                raise
            _, scene = generate_scene_video(fallback, store, project_uuid, scene, width=config_data.video.width, height=config_data.video.height, fps=config_data.video.fps, seed=seed)
    store.write_json(directory, f"scene-{scene.index:04d}.json", scene.model_dump(mode="json"))
    report = validate_project(store, project_uuid)
    _write_project_qa(store, project_uuid, report)
    if not report.passed:
        raise typer.Exit(code=1)
    typer.echo(f"Regenerated scene {scene.index}: {stage}; QA: PASS")


@app.command("subtitles")
def subtitles(project_id: str, max_chars: int = typer.Option(48, "--max-chars", min=1), config: Path | None = typer.Option(None, "--config", exists=True)) -> None:
    """Generate deterministic SRT and WebVTT subtitles."""
    store = FilesystemStore(load_config(config).storage.root)
    outputs = build_subtitles(store, UUID(project_id), _load_scenes(store, UUID(project_id)), max_chars=max_chars)
    for name, path in outputs.items():
        typer.echo(f"Generated {name}: {path}")


@app.command("timeline")
def timeline(project_id: str, config: Path | None = typer.Option(None, "--config", exists=True)) -> None:
    """Build and persist the deterministic timeline."""
    store = FilesystemStore(load_config(config).storage.root)
    project_uuid = UUID(project_id)
    result = build_timeline(store, store.load_project(project_uuid), _load_scenes(store, project_uuid))
    typer.echo(f"Generated timeline: {store.project_dir(project_uuid) / 'timeline.json'}")
    typer.echo(f"Scenes: {len(result.scenes)}")


@app.command("render")
def render(project_id: str, config: Path | None = typer.Option(None, "--config", exists=True)) -> None:
    """Render the persisted timeline to final.mp4."""
    store = FilesystemStore(load_config(config).storage.root)
    project_uuid = UUID(project_id)
    path = store.project_dir(project_uuid) / "timeline.json"
    if not path.is_file():
        raise typer.BadParameter("timeline.json not found; run 'video-agent timeline' first")
    timeline_data = Timeline.model_validate_json(path.read_text(encoding="utf-8"))
    artifact = FFmpegRenderer().render(store, project_uuid, timeline_data)
    typer.echo(f"Rendered video artifact: {artifact.id}")
    typer.echo(f"Output: {artifact.path}")


@app.command("acceptance")
def acceptance(project_id: str | None = typer.Option(None, "--project-id"), no_media: bool = typer.Option(False, "--no-media"), report_path: Path | None = typer.Option(None, "--report", help="Write JSON report to this path."), config: Path | None = typer.Option(None, "--config", exists=True)) -> None:
    """Run target-machine readiness and optional real local media acceptance."""
    config_data = load_config(config)
    report = run_acceptance(config_data, UUID(project_id) if project_id else None, execute_media=not no_media)
    output = write_report(report, report_path or config_data.storage.root / "acceptance-report.json")
    for check in report.checks:
        typer.echo(f"[{'PASS' if check.passed else 'FAIL'}] {check.name}: {check.detail}")
    typer.echo(f"Report: {output}")
    if not report.passed:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
