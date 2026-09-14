"""Resource and local runtime preflight checks."""

from dataclasses import dataclass
import os
from pathlib import Path
import shutil


@dataclass(frozen=True)
class ResourceSnapshot:
    """Point-in-time local resource information."""

    total_memory_bytes: int
    available_memory_bytes: int
    free_disk_bytes: int


def _memory_bytes() -> tuple[int, int]:
    """Return total and available physical memory on macOS when possible."""
    total = int(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"))
    available = int(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_AVPHYS_PAGES"))
    return total, available


def snapshot(storage_root: Path) -> ResourceSnapshot:
    """Capture memory and disk information without invoking external services."""
    total, available = _memory_bytes()
    free_disk = shutil.disk_usage(storage_root).free
    return ResourceSnapshot(total, available, free_disk)


def memory_gib(value: int) -> float:
    """Convert bytes to GiB for human-readable diagnostics."""
    return value / (1024**3)
