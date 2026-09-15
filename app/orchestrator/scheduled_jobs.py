"""Resource-aware wrapper around the persistent media job manager."""

from __future__ import annotations

import logging
from threading import Lock
from uuid import UUID

from app.config import load_config
from app.orchestrator.events import append_job_event
from app.orchestrator.jobs import MediaJob, MediaJobManager
from app.orchestrator.resource_scheduler import ResourceScheduler
from app.providers.capabilities import get_provider_capabilities
from app.storage.filesystem import FilesystemStore

logger = logging.getLogger(__name__)


class ScheduledMediaJobManager(MediaJobManager):
    """Admit media jobs according to current local memory pressure."""

    def __init__(self, store: FilesystemStore, *, max_workers: int = 2) -> None:
        super().__init__(store, max_workers=max_workers)
        self._resource_scheduler = ResourceScheduler(store)

    def _run(self, job_id: UUID) -> None:
        job = self.get(job_id)
        config = load_config(None)
        capability = get_provider_capabilities(config.video.provider).video
        logger.info(
            "[media] scheduler WAIT job=%s provider=%s memory_class=%s",
            job_id,
            config.video.provider,
            capability.memory_class,
        )
        _emit(
            self.store,
            job.project_id,
            "resource_wait",
            job_id=job_id,
            stage="media",
            state="queued",
            details={
                "provider": config.video.provider,
                "memory_class": capability.memory_class,
            },
        )
        with self._resource_scheduler.reserve(str(job_id), capability) as reservation:
            logger.info(
                "[media] scheduler ADMIT job=%s reserved_gib=%.1f available_gib=%.1f",
                job_id,
                reservation.reserved_memory_gib,
                reservation.available_memory_gib,
            )
            _emit(
                self.store,
                job.project_id,
                "resource_admitted",
                job_id=job_id,
                stage="media",
                state="running",
                details={
                    "reserved_memory_gib": reservation.reserved_memory_gib,
                    "available_memory_gib": reservation.available_memory_gib,
                },
            )
            super()._run(job_id)
        final_job = self.get(job_id)
        _emit(
            self.store,
            final_job.project_id,
            "resource_released",
            job_id=job_id,
            stage="media",
            state=final_job.state,
        )
        _emit(
            self.store,
            final_job.project_id,
            "job_completed" if final_job.state == "completed" else "job_failed",
            job_id=job_id,
            state=final_job.state,
            details={"error": final_job.error} if final_job.error else {},
        )
        logger.info("[media] scheduler RELEASE job=%s", job_id)

    def resource_snapshot(self) -> tuple[object, ...]:
        """Return active scheduler reservations for local diagnostics."""
        return self._resource_scheduler.active()


def _emit(
    store: FilesystemStore,
    project_id: UUID,
    event: str,
    *,
    job_id: UUID,
    stage: str | None = None,
    state: str | None = None,
    details: dict[str, object] | None = None,
) -> None:
    try:
        append_job_event(
            store.root,
            project_id,
            event,
            job_id=job_id,
            stage=stage,
            state=state,
            details=details,
        )
    except Exception:  # pragma: no cover - diagnostics must never break execution
        logger.exception("[events] failed to append event=%s job=%s", event, job_id)


_manager: ScheduledMediaJobManager | None = None
_manager_lock = Lock()


def get_scheduled_job_manager(store: FilesystemStore) -> ScheduledMediaJobManager:
    """Return the process-local resource-aware worker manager."""
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = ScheduledMediaJobManager(store)
        return _manager
