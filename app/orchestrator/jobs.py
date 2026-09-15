"""Persistent background job orchestration for local media generation."""

from datetime import datetime, timezone
import logging
from threading import Lock
from uuid import UUID, uuid4
from concurrent.futures import Future, ThreadPoolExecutor
from typing import List

from app.config import load_config
from app.generation.image_recovery import generate_scene_image_with_recovery
from app.generation.video_recovery import generate_scene_video_with_recovery
from app.models.job import MediaJob
from app.models.scene import Scene
from app.orchestrator.media_generation import generate_project_media
from app.providers.capabilities import get_provider_capabilities
from app.providers.diffusers_image import DiffusersImageProvider
from app.providers.factory import build_video_fallback, build_video_provider
from app.storage.filesystem import FilesystemStore

logger = logging.getLogger(__name__)


class MediaJobManager:
    """Manage durable local media jobs with bounded worker concurrency."""

    def __init__(self, store: FilesystemStore, max_workers: int = 1) -> None:
        self.store = store
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="media")
        self._futures: dict[UUID, Future[None]] = {}
        self._lock = Lock()

    def _job_path(self, job_id: UUID):
        return self.store.root / "jobs" / f"{job_id}.json"

    def _save(self, job: MediaJob) -> MediaJob:
        self.store.write_json(self.store.root / "jobs", f"{job.id}.json", job.model_dump(mode="json"))
        return job

    def get(self, job_id: UUID) -> MediaJob:
        path = self._job_path(job_id)
        if not path.is_file():
            raise FileNotFoundError(job_id)
        return MediaJob.model_validate_json(path.read_text(encoding="utf-8"))

    def list(self, project_id: UUID) -> List[MediaJob]:
        jobs: List[MediaJob] = []
        jobs_dir = self.store.root / "jobs"
        if not jobs_dir.exists():
            return jobs
        for path in sorted(jobs_dir.glob("*.json")):
            try:
                job = MediaJob.model_validate_json(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if job.project_id == project_id:
                jobs.append(job)
        return jobs

    def submit(self, project_id: UUID) -> MediaJob:
        scenes = self._load_scenes(project_id)
        now = datetime.now(timezone.utc)
        job = MediaJob(
            id=uuid4(),
            project_id=project_id,
            state="queued",
            created_at=now,
            updated_at=now,
            scene_count=len(scenes),
        )
        self._save(job)
        logger.info(
            "[media] submitted job=%s project=%s scene_count=%s state=queued",
            job.id,
            project_id,
            len(scenes),
        )
        future = self._executor.submit(self._run, job.id)
        with self._lock:
            self._futures[job.id] = future
        return job

    def _load_scenes(self, project_id: UUID) -> List[Scene]:
        scenes: List[Scene] = []
        for path in sorted(self.store.project_dir(project_id).glob("scene-*.json")):
            if path.name.endswith(("-image.json", "-audio.json", "-video.json")):
                continue
            try:
                scenes.append(Scene.model_validate_json(path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                logger.warning("[media] skipping invalid scene file=%s", path.name)
        logger.info("[media] loaded scenes project=%s count=%s", project_id, len(scenes))
        if not scenes:
            raise ValueError(f"no scenes found: {project_id}")
        return scenes

    def _update(self, job_id: UUID, **changes: object) -> MediaJob:
        current = self.get(job_id)
        updated = current.model_copy(update={**changes, "updated_at": datetime.now(timezone.utc)})
        logger.info(
            "[media] job=%s state=%s progress=%s/%s",
            job_id,
            updated.state,
            updated.completed_scenes,
            updated.scene_count,
        )
        return self._save(updated)

    def _run(self, job_id: UUID) -> None:
        job = self._update(
            job_id, state="running", started_at=datetime.now(timezone.utc), error=None
        )
        logger.info("[media] worker START job=%s project=%s", job.id, job.project_id)
        try:
            logger.info("[media] loading configuration job=%s", job_id)
            config = load_config(None)
            scenes = self._load_scenes(job.project_id)
            logger.info(
                "[media] config image=%s video=%s device=%s",
                config.image.model_path,
                config.video.provider,
                config.image.device,
            )
            if not config.runtime.local_only:
                raise ValueError("local_only must remain enabled")
            logger.info("[media] initializing video provider=%s", config.video.provider)
            video_provider = build_video_provider(config)

            # Image generation is optional when every scene already has a persisted
            # image asset. Do not initialize Diffusers just to process existing assets;
            # this keeps resume/media jobs independent of an unused image model.
            image_provider = None
            if any(scene.image_asset is None for scene in scenes):
                logger.info(
                    "[media] initializing image provider model=%s because image assets are missing",
                    config.image.model_path,
                )
                image_provider = DiffusersImageProvider(
                    config.image.model_path, device=config.image.device
                )
            else:
                logger.info("[media] all scenes already have image assets; image provider not required")

            capability = get_provider_capabilities(config.video.provider).video
            logger.info("[media] provider capability=%s", capability)

            def progress(completed: int, total: int) -> None:
                logger.info(
                    "[media] progress job=%s completed=%s total=%s", job_id, completed, total
                )
                self._update(job_id, completed_scenes=completed, scene_count=total)

            logger.info("[media] generation START job=%s", job_id)
            generate_project_media(
                self.store,
                job.project_id,
                scenes,
                video_provider=video_provider,
                image_provider=image_provider,
                image_model=config.image.model_path.name,
                image_width=config.image.width,
                image_height=config.image.height,
                image_steps=config.image.steps,
                image_guidance_scale=config.image.guidance_scale,
                video_capability=capability,
                fallback_provider=build_video_fallback(config),
                width=config.video.width,
                height=config.video.height,
                fps=config.video.fps,
                progress_callback=progress,
            )
            self._update(
                job_id,
                state="completed",
                completed_scenes=job.scene_count,
                completed_at=datetime.now(timezone.utc),
            )
            logger.info("[media] worker COMPLETE job=%s project=%s", job.id, job.project_id)
        except Exception as exc:
            logger.exception(
                "[media] worker FAILED job=%s project=%s error=%s", job.id, job.project_id, exc
            )
            self._update(
                job_id, state="failed", error=str(exc), completed_at=datetime.now(timezone.utc)
            )
        finally:
            with self._lock:
                self._futures.pop(job_id, None)
            logger.info("[media] worker EXIT job=%s", job_id)


_manager: MediaJobManager | None = None
_manager_lock = Lock()


def get_job_manager(store: FilesystemStore) -> MediaJobManager:
    """Return the process-wide media job manager."""
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = MediaJobManager(store)
        return _manager
