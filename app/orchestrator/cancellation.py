"""Cooperative cancellation state for local background jobs."""

from __future__ import annotations

from threading import Event, Lock
from uuid import UUID


class JobCancellationRequested(RuntimeError):
    """Raised at a safe orchestration boundary after a job is cancelled."""


class CancellationRegistry:
    """Process-local cancellation registry with explicit job lifecycle."""

    def __init__(self) -> None:
        self._events: dict[UUID, Event] = {}
        self._lock = Lock()

    def register(self, job_id: UUID) -> Event:
        with self._lock:
            return self._events.setdefault(job_id, Event())

    def cancel(self, job_id: UUID) -> bool:
        with self._lock:
            event = self._events.get(job_id)
            if event is None:
                return False
            event.set()
            return True

    def is_cancelled(self, job_id: UUID) -> bool:
        with self._lock:
            event = self._events.get(job_id)
            return event.is_set() if event else False

    def check(self, job_id: UUID) -> None:
        if self.is_cancelled(job_id):
            raise JobCancellationRequested(f"job {job_id} cancellation requested")

    def discard(self, job_id: UUID) -> None:
        with self._lock:
            self._events.pop(job_id, None)
