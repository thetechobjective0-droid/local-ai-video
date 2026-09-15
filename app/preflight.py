"""Resource and local runtime preflight checks."""

from dataclasses import dataclass
import os
from pathlib import Path
import platform
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


def _memory_bytes_macos() -> tuple[int, int]:
    """Return total and available physical memory on macOS."""
    total = int(
        subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip()
    )

    vm_stat = subprocess.check_output(["vm_stat"], text=True)
    page_size = 4096
    stats: dict[str, int] = {}

    for line in vm_stat.splitlines():
        if line.startswith("page size of"):
            page_size = int(line.split()[-2])
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip().rstrip(".")
        try:
            stats[key] = int(value)
        except ValueError:
            continue

    available_pages = (
        stats.get("Pages free", 0)
        + stats.get("Pages inactive", 0)
        + stats.get("Pages speculative", 0)
    )
    available = max(0, available_pages * page_size)
    return total, available


def _memory_bytes() -> tuple[int, int]:
    """Return total and available physical memory across supported platforms."""
    if platform.system() == "Darwin":
        try:
            return _memory_bytes_macos()
        except (OSError, ValueError, subprocess.CalledProcessError):
            pass

    page_size = _sysconf_memory("SC_PAGE_SIZE")
    physical_pages = _sysconf_memory("SC_PHYS_PAGES")
    available_pages = _sysconf_memory("SC_AVPHYS_PAGES")
    if page_size and physical_pages and available_pages:
        return page_size * physical_pages, page_size * available_pages

    if hasattr(os, "getloadavg") and page_size and physical_pages:
        total = page_size * physical_pages
        return total, total

    if shutil.which("sysctl"):
        try:
            total = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
            return total, total
        except (OSError, ValueError, subprocess.CalledProcessError):
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
