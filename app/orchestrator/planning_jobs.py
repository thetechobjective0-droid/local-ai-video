"""Persistent local background jobs for LLM project planning."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock
from uuid import UUID, uuid4
import tempfile

from pydantic import BaseModel, ConfigDict, Field

from app.config import load_config
from app.director.project import _run_plan
from app.models.project import ProjectStatus
from app.providers.ollama import OllamaProvider
from app.storage.filesystem import FilesystemStore


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
        return self._save(
            current.model_copy(update={**changes, "updated_at": datetime.now(timezone.utc)})
        )

    def get(self, job_id: UUID) -> PlanningJob:
        path = self._path(job_id)
        if not path.is_file():
            raise FileNotFoundError(str(job_id))
        return PlanningJob.model_validate_json(path.read_text(encoding="utf-8"))

    def submit(self, project_id: UUID) -> PlanningJob:
        now = datetime.now(timezone.utc)
        job = PlanningJob(
            id=uuid4(), project_id=project_id, state="queued", created_at=now, updated_at=now
        )
        self._save(job)
        self._executor.submit(self._run, job.id)
        return job

    def _run(self, job_id: UUID) -> None:
        self._update(job_id, state="running")
        job = self.get(job_id)
        try:
            config = load_config(None)
            if not config.runtime.local_only or config.llm.provider != "ollama":
                raise ValueError("local Ollama provider is required")
            provider = OllamaProvider(config.llm.base_url)
            provider.require_health()
            provider.require_model(config.llm.model)
            project = self.store.load_project(job.project_id)
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
            self._update(job_id, state="completed", completed_stage="storyboard")
        except Exception as exc:
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
                except (OSError, ValueError):
                    pass


_manager: PlanningJobManager | None = None
_manager_lock = Lock()


def get_planning_job_manager(store: FilesystemStore) -> PlanningJobManager:
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = PlanningJobManager(store)
        return _manager
