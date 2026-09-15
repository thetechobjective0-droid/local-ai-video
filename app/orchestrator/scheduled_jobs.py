"""Resource-aware wrapper around the persistent media job manager."""

from __future__ import annotations

import logging
from threading import Lock
from uuid import UUID

from app.config import load_config
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
        config = load_config(None)
        capability = get_provider_capabilities(config.video.provider).video
        logger.info(
            "[media] scheduler WAIT job=%s provider=%s memory_class=%s",
            job_id,
            config.video.provider,
            capability.memory_class,
        )
        with self._resource_scheduler.reserve(str(job_id), capability) as reservation:
            logger.info(
                "[media] scheduler ADMIT job=%s reserved_gib=%.1f available_gib=%.1f",
                job_id,
                reservation.reserved_memory_gib,
                reservation.available_memory_gib,
            )
            super()._run(job_id)
        logger.info("[media] scheduler RELEASE job=%s", job_id)

    def resource_snapshot(self) -> tuple[object, ...]:
        """Return active scheduler reservations for local diagnostics."""
        return self._resource_scheduler.active()


_manager: ScheduledMediaJobManager | None = None
_manager_lock = Lock()


def get_scheduled_job_manager(store: FilesystemStore) -> ScheduledMediaJobManager:
    """Return the process-local resource-aware worker manager."""
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = ScheduledMediaJobManager(store)
        return _manager
