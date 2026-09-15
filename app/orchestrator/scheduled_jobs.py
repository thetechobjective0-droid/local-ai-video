"""Resource-aware wrapper around the persistent media job manager."""

from __future__ import annotations

import logging
from threading import Lock
from uuid import UUID

from app.config import load_config
from app.orchestrator.cancellation import JobCancellationRequested
from app.orchestrator.events import append_job_event
from app.orchestrator.jobs import MediaJobManager
from app.orchestrator.resource_scheduler import ResourceReservation, ResourceScheduler
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
        _emit(self.store, job.project_id, "resource_wait", job_id=job_id, stage="media", state="queued", details={"provider": config.video.provider, "memory_class": capability.memory_class})
        try:
            with self._resource_scheduler.reserve(str(job_id), capability, cancelled=lambda: self._cancellation.is_cancelled(job_id)) as reservation:
                _emit(self.store, job.project_id, "resource_admitted", job_id=job_id, stage="media", state="running", details={"reserved_memory_gib": reservation.reserved_memory_gib, "available_memory_gib": reservation.available_memory_gib})
                super()._run(job_id)
        except JobCancellationRequested as exc:
            current = self.get(job_id)
            if current.state not in {"completed", "failed", "cancelled"}:
                self._update(job_id, state="cancelled", error=str(exc))
        except Exception as exc:
            logger.exception("[media] scheduler failed job=%s error=%s", job_id, exc)
            try:
                current = self.get(job_id)
                if current.state not in {"cancelled", "completed", "failed"}:
                    self._update(job_id, state="failed", error=str(exc))
            except FileNotFoundError:
                return
        finally:
            try:
                final_job = self.get(job_id)
                _emit(self.store, final_job.project_id, "resource_released", job_id=job_id, stage="media", state=final_job.state)
            except FileNotFoundError:
                pass

    def resource_snapshot(self) -> tuple[ResourceReservation, ...]:
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
        append_job_event(store.root, project_id, event, job_id=job_id, stage=stage, state=state, details=details)
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
