"""Persistent local background jobs for LLM project planning."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock
from uuid import UUID, uuid4
import tempfile
import logging

from pydantic import BaseModel, ConfigDict, Field

from app.config import load_config
from app.director.project import _run_plan, resume_plan
from app.models.project import ProjectStatus
from app.providers.ollama import OllamaProvider
from app.storage.filesystem import FilesystemStore

logger = logging.getLogger(__name__)


class PlanningJob(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    project_id: UUID
    state: str = Field(pattern="^(queued|running|completed|failed)$")
    created_at: datetime
    updated_at: datetime
    completed_stage: str | None = None
    error: str | None = None


class PlanningJobManager:
    """Single local worker for non-blocking Ollama project planning."""

    def __init__(self, store: FilesystemStore) -> None:
        self.store = store
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="video-agent-plan")
        self._lock = Lock()
        logger.info("[planning] manager initialized: worker_count=1 storage=%s", store.root)

    def _path(self, job_id: UUID) -> Path:
        jobs_dir = self.store.root / "planning-jobs"
        jobs_dir.mkdir(parents=True, exist_ok=True)
        return jobs_dir / f"{job_id}.json"

    def _save(self, job: PlanningJob) -> PlanningJob:
        path = self._path(job.id)
        payload = json.dumps(job.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=".job-", delete=False
        ) as temp:
            temp.write(payload)
            temp_path = Path(temp.name)
        temp_path.replace(path)
        return job

    def _update(self, job_id: UUID, **changes: object) -> PlanningJob:
        current = self.get(job_id)
        updated = current.model_copy(update={**changes, "updated_at": datetime.now(timezone.utc)})
        logger.info(
            "[planning] job=%s state=%s%s",
            job_id,
            updated.state,
            f" completed_stage={updated.completed_stage}" if updated.completed_stage else "",
        )
        return self._save(updated)

    def get(self, job_id: UUID) -> PlanningJob:
        path = self._path(job_id)
        if not path.is_file():
            raise FileNotFoundError(str(job_id))
        return PlanningJob.model_validate_json(path.read_text(encoding="utf-8"))

    def list(self, project_id: UUID | None = None) -> list[PlanningJob]:
        jobs_dir = self.store.root / "planning-jobs"
        jobs: list[PlanningJob] = []
        for path in sorted(jobs_dir.glob("*.json") if jobs_dir.exists() else []):
            try:
                job = PlanningJob.model_validate_json(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if project_id is None or job.project_id == project_id:
                jobs.append(job)
        return sorted(jobs, key=lambda item: item.created_at, reverse=True)

    def submit(self, project_id: UUID) -> PlanningJob:
        now = datetime.now(timezone.utc)
        job = PlanningJob(
            id=uuid4(), project_id=project_id, state="queued", created_at=now, updated_at=now
        )
        self._save(job)
        logger.info("[planning] submitted job=%s project=%s state=queued", job.id, project_id)
        self._executor.submit(self._run, job.id)
        return job

    def _run(self, job_id: UUID) -> None:
        self._update(job_id, state="running")
        job = self.get(job_id)
        logger.info("[planning] started job=%s project=%s", job.id, job.project_id)
        try:
            logger.info("[planning] loading configuration job=%s", job_id)
            config = load_config(None)
            logger.info(
                "[planning] config local_only=%s provider=%s model=%s temperature=%s top_p=%s top_k=%s",
                config.runtime.local_only,
                config.llm.provider,
                config.llm.model,
                config.llm.temperature,
                config.llm.top_p,
                config.llm.top_k,
            )
            if not config.runtime.local_only or config.llm.provider != "ollama":
                raise ValueError("local Ollama provider is required")
            provider = OllamaProvider(config.llm.base_url)
            logger.info("[planning] checking Ollama health endpoint=%s", config.llm.base_url)
            provider.require_health()
            logger.info("[planning] Ollama health check passed")
            logger.info("[planning] checking configured model=%s", config.llm.model)
            provider.require_model(config.llm.model)
            logger.info("[planning] model is installed: %s", config.llm.model)
            project = self.store.load_project(job.project_id)
            logger.info(
                "[planning] loaded project=%s duration=%ss style=%s aspect_ratio=%s",
                project.id,
                project.duration_seconds,
                project.style,
                project.aspect_ratio,
            )
            try:
                logger.info("[planning] pipeline start_from=brief project=%s", project.id)
                _run_plan(
                    provider,
                    self.store,
                    self.store.project_dir(job.project_id),
                    project,
                    model=config.llm.model,
                    temperature=config.llm.temperature,
                    top_p=config.llm.top_p,
                    top_k=config.llm.top_k,
                    start_from="brief",
                )
            except Exception as first_error:
                logger.warning(
                    "[planning] first pipeline attempt failed project=%s error=%s; starting bounded resume retry",
                    project.id,
                    first_error,
                )
                try:
                    resume_plan(
                        provider,
                        self.store,
                        str(job.project_id),
                        model=config.llm.model,
                        temperature=config.llm.temperature,
                        top_p=config.llm.top_p,
                        top_k=config.llm.top_k,
                    )
                except Exception as retry_error:
                    logger.exception(
                        "[planning] retry failed project=%s error=%s", project.id, retry_error
                    )
                    raise RuntimeError(
                        f"planning failed after retry: first attempt: {first_error}; "
                        f"retry: {retry_error}"
                    ) from retry_error
                logger.info("[planning] resume retry completed project=%s", project.id)
            self._update(job_id, state="completed", completed_stage="storyboard", error=None)
            logger.info(
                "[planning] completed job=%s project=%s stage=storyboard", job.id, job.project_id
            )
        except Exception as exc:
            logger.exception(
                "[planning] failed job=%s project=%s error=%s", job.id, job.project_id, exc
            )
            try:
                self._update(job_id, state="failed", error=str(exc))
            finally:
                try:
                    project = self.store.load_project(job.project_id)
                    project.status = ProjectStatus.FAILED
                    project.updated_at = datetime.now(timezone.utc)
                    self.store.write_json(
                        self.store.project_dir(job.project_id),
                        "project.json",
                        project.model_dump(mode="json"),
                    )
                    logger.info("[planning] project marked failed project=%s", project.id)
                except (OSError, ValueError):
                    logger.exception(
                        "[planning] could not persist failed project status project=%s",
                        job.project_id,
                    )


_manager: PlanningJobManager | None = None
_manager_lock = Lock()


def get_planning_job_manager(store: FilesystemStore) -> PlanningJobManager:
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = PlanningJobManager(store)
        return _manager
