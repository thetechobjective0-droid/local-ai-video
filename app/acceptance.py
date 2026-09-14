"""Repeatable target-machine acceptance for the local media pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import platform
from time import monotonic
from typing import Any
from uuid import UUID

from app.config import AppConfig
from app.generation.images import generate_scene_image
from app.generation.video import generate_scene_video
from app.models.scene import Scene
from app.models.timeline import Timeline
from app.preflight import snapshot
from app.providers.diffusers_image import DiffusersImageProvider
from app.providers.factory import build_video_provider
from app.qa.project import validate_project
from app.render.ffmpeg import FFmpegRenderer
from app.storage.filesystem import FilesystemStore


@dataclass(frozen=True)
class AcceptanceCheck:
    name: str
    passed: bool
    detail: str
    seconds: float | None = None


@dataclass(frozen=True)
class AcceptanceReport:
    """Machine-readable result of one target-machine acceptance run."""

    passed: bool
    platform: str
    machine: str
    checks: tuple[AcceptanceCheck, ...]
    resource_before: dict[str, int]
    resource_after: dict[str, int]
    report_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_version": self.report_version,
            "passed": self.passed,
            "platform": self.platform,
            "machine": self.machine,
            "checks": [asdict(check) for check in self.checks],
            "resource_before": self.resource_before,
            "resource_after": self.resource_after,
        }


def model_readiness(path: Path) -> tuple[bool, str]:
    """Check that a downloaded local Diffusers model is plausibly complete."""
    path = path.expanduser().resolve()
    if not path.is_dir():
        return False, f"model directory does not exist: {path}"
    marker_files = [path / "model_index.json", path / "config.json"]
    if not any(item.is_file() for item in marker_files):
        return False, f"missing Diffusers model metadata under {path}"
    weights = [
        item
        for item in path.rglob("*")
        if item.is_file() and item.suffix in {".safetensors", ".bin", ".ckpt", ".pth"}
    ]
    if not weights:
        return False, f"no model weight files found under {path}"
    total = sum(item.stat().st_size for item in weights)
    if total <= 0:
        return False, f"model weight files are empty under {path}"
    return True, f"{len(weights)} weight files, {total / (1024**3):.2f} GiB"


def _mps_readiness(device: str) -> tuple[bool, str]:
    if device != "mps":
        return True, f"device={device}; MPS check not required"
    try:
        import torch
    except ImportError:
        return False, "PyTorch is not installed; install the image optional dependencies"
    available = bool(torch.backends.mps.is_available())
    detail = f"torch={torch.__version__}; mps_available={available}"
    return available, detail


def _scene(store: FilesystemStore, project_id: UUID) -> Scene:
    directory = store.project_dir(project_id)
    scenes: list[Scene] = []
    for path in sorted(directory.glob("scene-*.json")):
        if path.name.endswith(("-image.json", "-audio.json", "-video.json")):
            continue
        try:
            scenes.append(Scene.model_validate_json(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    if not scenes:
        raise ValueError(f"no scenes found: {project_id}")
    return sorted(scenes, key=lambda item: item.index)[0]


def _timeline(store: FilesystemStore, project_id: UUID) -> Timeline:
    path = store.project_dir(project_id) / "timeline.json"
    if not path.is_file():
        raise ValueError("timeline.json is missing")
    return Timeline.model_validate_json(path.read_text(encoding="utf-8"))


def _resource_dict(resources: Any) -> dict[str, int]:
    return {
        "total_memory_bytes": int(resources.total_memory_bytes),
        "available_memory_bytes": int(resources.available_memory_bytes),
        "free_disk_bytes": int(resources.free_disk_bytes),
    }


def run_acceptance(
    config: AppConfig,
    project_id: UUID | None = None,
    *,
    execute_media: bool = True,
) -> AcceptanceReport:
    """Run readiness checks and, when requested, one real local media path."""
    checks: list[AcceptanceCheck] = []
    before = snapshot(config.storage.root)

    def add(name: str, passed: bool, detail: str, seconds: float | None = None) -> None:
        checks.append(AcceptanceCheck(name, passed, detail, seconds))

    add("local_only", config.runtime.local_only, "local_only must remain enabled")
    add("platform", platform.system() == "Darwin", f"{platform.system()} {platform.machine()}")
    add("apple_silicon", platform.machine() in {"arm64", "aarch64"}, platform.machine())
    add("ffmpeg", _command_available("ffmpeg"), _command_path("ffmpeg"))
    add("ffprobe", _command_available("ffprobe"), _command_path("ffprobe"))
    add("image_model", *model_readiness(config.image.model_path))
    add("image_device", *_mps_readiness(config.image.device))

    if project_id is not None and execute_media:
        store = FilesystemStore(config.storage.root)
        try:
            scene = _scene(store, project_id)
            start = monotonic()
            image_provider = DiffusersImageProvider(
                config.image.model_path, device=config.image.device
            )
            load_start = monotonic()
            image_provider._load_pipeline()
            add(
                "image_model_load",
                True,
                f"loaded {config.image.model_path}",
                monotonic() - load_start,
            )
            image_artifact, scene = generate_scene_image(
                image_provider,
                store,
                project_id,
                scene,
                model=config.image.model_path.name,
                width=config.image.width,
                height=config.image.height,
                steps=config.image.steps,
                guidance_scale=config.image.guidance_scale,
            )
            add(
                "image_generation",
                image_artifact.path.is_file() and image_artifact.path.stat().st_size > 0,
                f"{image_artifact.path.name}; {image_artifact.parameters.get('width')}x{image_artifact.parameters.get('height')}",
                monotonic() - start,
            )

            video_provider = build_video_provider(config)
            video_load_start = monotonic()
            load = getattr(video_provider, "_load_pipeline", None)
            if callable(load):
                load()
                add(
                    "video_model_load",
                    True,
                    "local video model loaded",
                    monotonic() - video_load_start,
                )
            else:
                add("video_model_load", True, "deterministic provider has no model-load stage")
            video_start = monotonic()
            video_artifact, _ = generate_scene_video(
                video_provider,
                store,
                project_id,
                scene,
                width=config.video.width,
                height=config.video.height,
                fps=config.video.fps,
            )
            add(
                "video_generation",
                video_artifact.path.is_file() and video_artifact.path.stat().st_size > 0,
                f"{video_artifact.path.name}; {video_artifact.parameters.get('width')}x{video_artifact.parameters.get('height')}@{video_artifact.parameters.get('fps')}",
                monotonic() - video_start,
            )

            report = validate_project(store, project_id)
            add(
                "project_qa",
                report.passed,
                "QA PASS" if report.passed else "; ".join(f.message for f in report.failures),
            )
            timeline = _timeline(store, project_id)
            render_start = monotonic()
            final_artifact = FFmpegRenderer().render(store, project_id, timeline)
            add(
                "final_render",
                final_artifact.path.is_file() and final_artifact.path.stat().st_size > 0,
                str(final_artifact.path),
                monotonic() - render_start,
            )
            final_qa = validate_project(store, project_id)
            add(
                "final_qa",
                final_qa.passed,
                "QA PASS" if final_qa.passed else "; ".join(f.message for f in final_qa.failures),
            )
        except Exception as exc:
            add("media_pipeline", False, f"{type(exc).__name__}: {exc}")

    after = snapshot(config.storage.root)
    return AcceptanceReport(
        passed=all(check.passed for check in checks),
        platform=platform.system(),
        machine=platform.machine(),
        checks=tuple(checks),
        resource_before=_resource_dict(before),
        resource_after=_resource_dict(after),
    )


def write_report(report: AcceptanceReport, path: Path) -> Path:
    """Persist an acceptance report as JSON."""
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path


def _command_available(command: str) -> bool:
    from shutil import which

    return which(command) is not None


def _command_path(command: str) -> str:
    from shutil import which

    return which(command) or "not found"
