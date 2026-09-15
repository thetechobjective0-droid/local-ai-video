"""Resource and local runtime preflight checks."""

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess


@dataclass(frozen=True)
class ResourceSnapshot:
    """Point-in-time local resource information."""

    total_memory_bytes: int
    available_memory_bytes: int
    free_disk_bytes: int


def _sysconf_memory(name: str) -> int | None:
    """Read a sysconf memory value when the platform exposes it."""
    try:
        return int(os.sysconf(name))
    except (ValueError, OSError, AttributeError):
        return None


def _memory_bytes() -> tuple[int, int]:
    """Return total and available physical memory across supported platforms."""
    page_size = _sysconf_memory("SC_PAGE_SIZE")
    physical_pages = _sysconf_memory("SC_PHYS_PAGES")
    available_pages = _sysconf_memory("SC_AVPHYS_PAGES")
    if page_size and physical_pages and available_pages:
        return page_size * physical_pages, page_size * available_pages

    if shutil.which("sysctl"):
        try:
            total = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
            free_pages = int(subprocess.check_output(["sysctl", "-n", "vm.swapusage"], text=True).split("free =", 1)[1].split("M", 1)[0].strip())
            available = max(0, int(free_pages * 1024 * 1024))
            return total, available
        except (OSError, ValueError, IndexError, subprocess.CalledProcessError):
            pass

    if hasattr(os, "getloadavg"):
        try:
            total = int(os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE"))
            return total, total
        except (ValueError, OSError, AttributeError):
            pass
    raise RuntimeError("unable to determine physical memory on this platform")


def snapshot(storage_root: Path) -> ResourceSnapshot:
    """Capture memory and disk information without invoking external services."""
    total, available = _memory_bytes()
    free_disk = shutil.disk_usage(storage_root).free
    return ResourceSnapshot(total, available, free_disk)


def memory_gib(value: int) -> float:
    """Convert bytes to GiB for human-readable diagnostics."""
    return value / (1024**3)
