"""Persistent local background job orchestration for project media generation."""

from __future__ import annotations

import json
import logging
import tempfile
import wave
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import List
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.config import AppConfig, load_config
from app.generation.audio import generate_scene_audio
from app.generation.subtitles import build_subtitles
from app.generation.timeline import build_timeline
from app.models.artifact import Artifact
from app.models.scene import Scene
from app.orchestrator.cancellation import CancellationRegistry, JobCancellationRequested
from app.orchestrator.checkpoint_runtime import CheckpointRuntime
from app.orchestrator.media_generation import generate_project_media
from app.providers.capabilities import get_provider_capabilities
from app.providers.diffusers_image import DiffusersImageProvider
from app.providers.factory import build_video_fallback, build_video_provider
from app.providers.image import ImageProvider
from app.providers.macos_tts import MacOSTTSProvider
from app.qa.project import validate_project
from app.qa.report import write_qa_report
from app.render.ffmpeg import FFmpegRenderer
from app.storage.filesystem import FilesystemStore

logger = logging.getLogger(__name__)


class MediaJob(BaseModel):
    """Durable state for one project media generation request."""

    model_config = ConfigDict(extra="forbid")
    id: UUID
    project_id: UUID
    state: str = Field(pattern="^(queued|running|completed|failed|interrupted|cancelled)$")
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    scene_count: int = 0
    completed_scenes: int = 0


def _build_image_provider_if_needed(config: AppConfig, scenes: List[Scene]) -> ImageProvider | None:
    if not any(scene.image_asset is None for scene in scenes):
        return None
    return DiffusersImageProvider(config.image.model_path, device=config.image.device)


def _audio_is_usable(store: FilesystemStore, project_id: UUID, scene: Scene) -> bool:
    if scene.audio_asset is None:
        return False
    directory = store.project_dir(project_id)
    manifest_path = directory / f"scene-{scene.index:04d}-audio.json"
    try:
        artifact = Artifact.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        if artifact.id != scene.audio_asset:
            return False
        path = artifact.path.expanduser()
        if not path.is_absolute():
            path = (directory / path).resolve()
        if directory.resolve() not in path.parents or not path.is_file():
            return False
        with wave.open(str(path), "rb") as audio:
            if audio.getnframes() <= 0:
                return False
            return bool(audio.readframes(audio.getnframes()))
    except (OSError, ValueError, wave.Error):
        return False


def _ensure_project_audio(store: FilesystemStore, project_id: UUID, scenes: list[Scene], config: AppConfig) -> list[Scene]:
    provider = MacOSTTSProvider(sample_rate=config.tts.sample_rate)
    refreshed: list[Scene] = []
    for scene in sorted(scenes, key=lambda item: item.index):
        current = scene
        if current.narration.strip() and not _audio_is_usable(store, project_id, current):
            configured_voice = current.metadata.get("voice")
            voice = configured_voice if isinstance(configured_voice, str) and configured_voice.strip() else config.tts.voice
            _, current = generate_scene_audio(
                provider,
                store,
                project_id,
                current,
                voice=voice,
                rate=config.tts.rate,
            )
        refreshed.append(current)
    return refreshed


def _finalize_project_media(store: FilesystemStore, project_id: UUID) -> None:
    project = store.load_project(project_id)
    scenes: list[Scene] = []
    for path in sorted(store.project_dir(project_id).glob("scene-*.json")):
        if path.name.endswith(("-image.json", "-audio.json", "-video.json")):
            continue
        try:
            scenes.append(Scene.model_validate_json(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    if not scenes:
        raise ValueError(f"no scenes found while finalizing project: {project_id}")
    build_timeline(store, project, scenes)
    build_subtitles(store, project_id, scenes)
    from app.models.timeline import Timeline
    timeline = Timeline.model_validate_json((store.project_dir(project_id) / "timeline.json").read_text(encoding="utf-8"))
    FFmpegRenderer().render(store, project_id, timeline)
    report = validate_project(store, project_id)
    write_qa_report(store.project_dir(project_id) / "qa-report.json", report)
    if not report.passed:
        failures = "; ".join(failure.message for failure in report.failures)
        raise ValueError(f"final project QA failed: {failures}")


class MediaJobManager:
    """Small in-process worker pool backed by atomic JSON job manifests."""

    def __init__(self, store: FilesystemStore, *, max_workers: int = 1) -> None:
        self.store = store
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="video-agent-job")
        self._futures: dict[UUID, Future[None]] = {}
        self._lock = Lock()
        self._cancellation = CancellationRegistry()
        self._recover_stale_jobs()

    def _path(self, job_id: UUID) -> Path:
        jobs_dir = self.store.root / "jobs"
        jobs_dir.mkdir(parents=True, exist_ok=True)
        path = (jobs_dir / f"{job_id}.json").resolve()
        if jobs_dir.resolve() not in path.parents:
            raise ValueError("job path escapes storage root")
        return path

    def _save(self, job: MediaJob) -> MediaJob:
        path = self._path(job.id)
        payload = json.dumps(job.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=".job-", delete=False) as temp:
            temp.write(payload)
            temp_path = Path(temp.name)
        temp_path.replace(path)
        return job

    def _recover_stale_jobs(self) -> None:
        jobs_dir = self.store.root / "jobs"
        for path in sorted(jobs_dir.glob("*.json") if jobs_dir.exists() else []):
            try:
                job = MediaJob.model_validate_json(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if job.state in {"queued", "running"}:
                self._save(job.model_copy(update={"state": "interrupted", "updated_at": datetime.now(timezone.utc), "error": "worker process restarted"}))

    def get(self, job_id: UUID) -> MediaJob:
        path = self._path(job_id)
        if not path.is_file():
            raise FileNotFoundError(str(job_id))
        return MediaJob.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def list(self, project_id: UUID | None = None) -> List[MediaJob]:
        jobs_dir = self.store.root / "jobs"
        result: List[MediaJob] = []
        for path in sorted(jobs_dir.glob("*.json") if jobs_dir.exists() else []):
            try:
                job = MediaJob.model_validate_json(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if project_id is None or job.project_id == project_id:
                result.append(job)
        return sorted(result, key=lambda item: item.created_at, reverse=True)

    def submit(self, project_id: UUID) -> MediaJob:
        scenes = self._load_scenes(project_id)
        now = datetime.now(timezone.utc)
        job = MediaJob(id=uuid4(), project_id=project_id, state="queued", created_at=now, updated_at=now, scene_count=len(scenes))
        self._save(job)
        self._cancellation.register(job.id)
        future = self._executor.submit(self._run, job.id)
        with self._lock:
            self._futures[job.id] = future
        return job

    def resume(self, job_id: UUID) -> MediaJob:
        job = self.get(job_id)
        if job.state not in {"interrupted", "failed", "cancelled"}:
            raise ValueError(f"job {job_id} is not resumable from state {job.state}")
        resumed = self._update(job_id, state="queued", error=None, completed_at=None)
        self._cancellation.register(job_id)
        with self._lock:
            future = self._futures.get(job_id)
            if future is not None and not future.done():
                raise ValueError(f"job {job_id} is already running")
            self._futures[job_id] = self._executor.submit(self._run, job_id)
        return resumed

    def cancel(self, job_id: UUID) -> MediaJob:
        job = self.get(job_id)
        if job.state in {"completed", "failed", "interrupted", "cancelled"}:
            return job
        self._cancellation.register(job_id)
        self._cancellation.cancel(job_id)
        if job.state == "queued":
            return self._update(job_id, state="cancelled", error="cancellation requested", completed_at=datetime.now(timezone.utc))
        return self._update(job_id, error="cancellation requested")

    def shutdown(self, *, wait: bool = True) -> None:
        for job in self.list():
            if job.state in {"queued", "running"}:
                self.cancel(job.id)
        self._executor.shutdown(wait=wait, cancel_futures=True)

    def _load_scenes(self, project_id: UUID) -> List[Scene]:
        scenes: List[Scene] = []
        for path in sorted(self.store.project_dir(project_id).glob("scene-*.json")):
            if path.name.endswith(("-image.json", "-audio.json", "-video.json")):
                continue
            try:
                scenes.append(Scene.model_validate_json(path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
        if not scenes:
            raise ValueError(f"no scenes found: {project_id}")
        return scenes

    def _update(self, job_id: UUID, **changes: object) -> MediaJob:
        current = self.get(job_id)
        return self._save(current.model_copy(update={**changes, "updated_at": datetime.now(timezone.utc)}))

    def _run(self, job_id: UUID) -> None:
        job = self._update(job_id, state="running", started_at=datetime.now(timezone.utc), error=None)
        runtime = CheckpointRuntime(self.store.root, job.project_id, job.id)
        runtime.emit("job_started", state="running")
        try:
            self._cancellation.check(job_id)
            config = load_config(None)
            scenes = self._load_scenes(job.project_id)
            if not config.runtime.local_only:
                raise ValueError("local_only must remain enabled")
            self._cancellation.check(job_id)
            if runtime.should_skip("audio"):
                scenes = self._load_scenes(job.project_id)
            else:
                runtime.begin("audio", 10, metadata={"scene_count": len(scenes)})
                scenes = _ensure_project_audio(self.store, job.project_id, scenes, config)
                runtime.complete("audio", artifacts=tuple(f"scene-{scene.index:04d}-audio.json" for scene in scenes if scene.audio_asset is not None))
            self._cancellation.check(job_id)
            if runtime.should_skip("media"):
                scenes = self._load_scenes(job.project_id)
                self._update(job_id, completed_scenes=len(scenes), scene_count=len(scenes))
            else:
                runtime.begin("media", 20, dependencies=("audio",))
                video_provider = build_video_provider(config)
                image_provider = _build_image_provider_if_needed(config, scenes)
                capability = get_provider_capabilities(config.video.provider).video

                def progress(completed: int, total: int) -> None:
                    self._cancellation.check(job_id)
                    self._update(job_id, completed_scenes=completed, scene_count=total)

                generate_project_media(self.store, job.project_id, scenes, video_provider=video_provider, image_provider=image_provider, image_model=config.image.model_path.name, image_width=config.image.width, image_height=config.image.height, image_steps=config.image.steps, image_guidance_scale=config.image.guidance_scale, video_capability=capability, fallback_provider=build_video_fallback(config), width=config.video.width, height=config.video.height, fps=config.video.fps, progress_callback=progress)
                scenes = self._load_scenes(job.project_id)
                runtime.complete("media", artifacts=tuple(f"scene-{scene.index:04d}.json" for scene in scenes), metadata={"scene_count": len(scenes)})
            self._cancellation.check(job_id)
            if not runtime.should_skip("finalize"):
                runtime.begin("finalize", 30, dependencies=("audio", "media"))
                _finalize_project_media(self.store, job.project_id)
                runtime.complete("finalize", artifacts=("timeline.json", "subtitles.srt", "final.mp4", "qa-report.json"))
            final_job = self._update(job_id, state="completed", completed_scenes=job.scene_count, completed_at=datetime.now(timezone.utc), error=None)
            runtime.emit("job_completed", state="completed")
            logger.info("[media] worker COMPLETE job=%s project=%s", final_job.id, final_job.project_id)
        except JobCancellationRequested as exc:
            cancelled = self._update(job_id, state="cancelled", error=str(exc), completed_at=datetime.now(timezone.utc))
            runtime.emit("job_cancelled", state="cancelled", details={"error": cancelled.error})
        except Exception as exc:
            logger.exception("[media] worker FAILED job=%s error=%s", job.id, exc)
            self._update(job_id, state="failed", error=str(exc), completed_at=datetime.now(timezone.utc))
            runtime.emit("job_failed", state="failed", details={"error": str(exc)})
        finally:
            with self._lock:
                self._futures.pop(job_id, None)
            self._cancellation.discard(job_id)


_manager: MediaJobManager | None = None
_manager_lock = Lock()


def get_job_manager(store: FilesystemStore) -> MediaJobManager:
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = MediaJobManager(store)
        return _manager
