"""Local resource-aware admission control for media jobs."""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from threading import Condition
from typing import Iterator

from app.orchestrator.media_strategy import VideoCapability
from app.preflight import ResourceSnapshot, snapshot
from app.storage.filesystem import FilesystemStore


@dataclass(frozen=True)
class ResourceReservation:
    """Admission decision recorded for one active media workload."""

    job_id: str
    memory_class: str
    reserved_memory_gib: float
    available_memory_gib: float


class _Reservation(AbstractContextManager[ResourceReservation]):
    def __init__(self, scheduler: "ResourceScheduler", reservation: ResourceReservation) -> None:
        self.scheduler = scheduler
        self.reservation = reservation

    def __enter__(self) -> ResourceReservation:
        return self.reservation

    def __exit__(self, exc_type, exc, tb) -> None:
        self.scheduler.release(self.reservation)
        return None


class ResourceScheduler:
    """Serialize heavyweight work when local unified-memory pressure is high."""

    def __init__(
        self,
        store: FilesystemStore,
        *,
        memory_headroom_gib: float = 4.0,
        low_reservation_gib: float = 2.0,
        high_reservation_gib: float = 8.0,
        max_high_concurrency: int = 1,
    ) -> None:
        if min(memory_headroom_gib, low_reservation_gib, high_reservation_gib) <= 0:
            raise ValueError("resource reservation values must be positive")
        if max_high_concurrency < 1:
            raise ValueError("max_high_concurrency must be positive")
        self.store = store
        self.memory_headroom_gib = memory_headroom_gib
        self.low_reservation_gib = low_reservation_gib
        self.high_reservation_gib = high_reservation_gib
        self.max_high_concurrency = max_high_concurrency
        self._condition = Condition()
        self._reservations: dict[str, ResourceReservation] = {}

    def reserve(
        self,
        job_id: str,
        capability: VideoCapability,
    ) -> AbstractContextManager[ResourceReservation]:
        """Block until the provider's memory class can be admitted safely."""
        memory_class = capability.memory_class if capability.memory_class in {"low", "high"} else "low"
        required = self.high_reservation_gib if memory_class == "high" else self.low_reservation_gib
        while True:
            resources = snapshot(self.store.root)
            available_gib = resources.available_memory_bytes / (1024**3)
            with self._condition:
                high_active = sum(
                    item.memory_class == "high" for item in self._reservations.values()
                )
                reserved = sum(item.reserved_memory_gib for item in self._reservations.values())
                capacity_ok = available_gib >= required + self.memory_headroom_gib
                reservation_ok = reserved + required <= max(
                    required,
                    available_gib - self.memory_headroom_gib,
                )
                high_ok = memory_class != "high" or high_active < self.max_high_concurrency
                if capacity_ok and reservation_ok and high_ok and job_id not in self._reservations:
                    reservation = ResourceReservation(
                        job_id=job_id,
                        memory_class=memory_class,
                        reserved_memory_gib=required,
                        available_memory_gib=available_gib,
                    )
                    self._reservations[job_id] = reservation
                    return _Reservation(self, reservation)
                self._condition.wait(timeout=1.0)

    def release(self, reservation: ResourceReservation) -> None:
        """Release a prior reservation and wake queued jobs."""
        with self._condition:
            self._reservations.pop(reservation.job_id, None)
            self._condition.notify_all()

    def active(self) -> tuple[ResourceReservation, ...]:
        """Return immutable admission state for local diagnostics."""
        with self._condition:
            return tuple(self._reservations.values())

    def __iter__(self) -> Iterator[ResourceReservation]:
        return iter(self.active())
