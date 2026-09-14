"""Persistent local background job orchestration for project media generation."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock
from uuid import UUID, uuid4
import tempfile

from pydantic import BaseModel, ConfigDict, Field

from app.config import load_config
from app.models.scene import Scene
from app.orchestrator.media_generation import generate_project_media
from app.providers.capabilities import get_provider_capabilities
from app.providers.factory import build_video_fallback, build_video_provider
from app.providers.diffusers_image import DiffusersImageProvider
from app.storage.filesystem import FilesystemStore


class MediaJob(BaseModel):
    """Durable state for one project media generation request."""

    model_config = ConfigDict(extra="forbid")
    id: UUID
    project_id: UUID
    state: str = Field(pattern="^(queued|running|completed|failed|interrupted)$")
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    scene_count: int = 0
    completed_scenes: int = 0


class MediaJobManager:
    """Small in-process worker pool backed by atomic JSON job manifests."""

    def __init__(self, store: FilesystemStore, *, max_workers: int = 1) -> None:
        self.store = store
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="video-agent-job"
        )
        self._futures: dict[UUID, Future[None]] = {}
        self._lock = Lock()
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
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=".job-", delete=False
        ) as temp:
            temp.write(payload)
            temp_path = Path(temp.name)
        temp_path.replace(path)
        return job

    def _recover_stale_jobs(self) -> None:
        """A new process cannot own old worker threads, so mark running jobs interrupted."""
        jobs_dir = self.store.root / "jobs"
        for path in sorted(jobs_dir.glob("*.json") if jobs_dir.exists() else []):
            try:
                job = MediaJob.model_validate_json(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if job.state in {"queued", "running"}:
                self._save(
                    job.model_copy(
                        update={
                            "state": "interrupted",
                            "updated_at": datetime.now(timezone.utc),
                            "error": "worker process restarted",
                        }
                    )
                )

    def get(self, job_id: UUID) -> MediaJob:
        path = self._path(job_id)
        if not path.is_file():
            raise FileNotFoundError(str(job_id))
        return MediaJob.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def list(self, project_id: UUID | None = None) -> list[MediaJob]:
        jobs_dir = self.store.root / "jobs"
        jobs: list[MediaJob] = []
        for path in sorted(jobs_dir.glob("*.json") if jobs_dir.exists() else []):
            try:
                job = MediaJob.model_validate_json(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if project_id is None or job.project_id == project_id:
                jobs.append(job)
        return sorted(jobs, key=lambda item: item.created_at, reverse=True)

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
        future = self._executor.submit(self._run, job.id)
        with self._lock:
            self._futures[job.id] = future
        return job

    def _load_scenes(self, project_id: UUID) -> list[Scene]:
        scenes: list[Scene] = []
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
        updated = current.model_copy(update={**changes, "updated_at": datetime.now(timezone.utc)})
        return self._save(updated)

    def _run(self, job_id: UUID) -> None:
        job = self._update(
            job_id, state="running", started_at=datetime.now(timezone.utc), error=None
        )
        try:
            config = load_config(None)
            if not config.runtime.local_only:
                raise ValueError("local_only must remain enabled")
            video_provider = build_video_provider(config)
            image_provider = DiffusersImageProvider(
                config.image.model_path, device=config.image.device
            )
            capability = get_provider_capabilities(config.video.provider).video

            def progress(completed: int, total: int) -> None:
                self._update(job_id, completed_scenes=completed, scene_count=total)

            generate_project_media(
                self.store,
                job.project_id,
                self._load_scenes(job.project_id),
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
        except Exception as exc:
            self._update(
                job_id, state="failed", error=str(exc), completed_at=datetime.now(timezone.utc)
            )
        finally:
            with self._lock:
                self._futures.pop(job_id, None)


_manager: MediaJobManager | None = None
_manager_lock = Lock()


def get_job_manager(store: FilesystemStore) -> MediaJobManager:
    """Return the process-local singleton worker manager."""
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = MediaJobManager(store)
        return _manager
