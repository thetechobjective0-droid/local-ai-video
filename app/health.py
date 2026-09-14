"""Local runtime health and preflight checks."""

from dataclasses import dataclass
import platform
import shutil
import sys

from app.config import AppConfig
from app.preflight import snapshot
from app.providers.ollama import OllamaProvider


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def check_platform() -> CheckResult:
    system = platform.system()
    machine = platform.machine()
    ok = system == "Darwin" and machine in {"arm64", "aarch64"}
    return CheckResult("apple_silicon", ok, f"{system} {machine}")


def check_python() -> CheckResult:
    version = sys.version.split()[0]
    return CheckResult("python", version != "", version)


def check_command(name: str) -> CheckResult:
    path = shutil.which(name)
    return CheckResult(name, path is not None, path or "not found")


def check_ollama(config: AppConfig) -> CheckResult:
    ok, detail = OllamaProvider().health()
    model_detail = f"; configured model={config.llm.model}" if ok else ""
    return CheckResult("ollama", ok, detail + model_detail)


def run_health_checks(config: AppConfig | None = None) -> list[CheckResult]:
    """Run local environment checks, including live Ollama reachability."""
    config = config or AppConfig()
    config.storage.root.mkdir(parents=True, exist_ok=True)
    resources = snapshot(config.storage.root)
    return [
        check_platform(),
        check_python(),
        check_command("ffmpeg"),
        check_ollama(config),
        CheckResult(
            "memory",
            resources.available_memory_bytes > 0,
            f"{resources.available_memory_bytes} bytes available",
        ),
        CheckResult(
            "disk", resources.free_disk_bytes > 0, f"{resources.free_disk_bytes} bytes free"
        ),
        CheckResult("storage", config.storage.root.exists(), str(config.storage.root.resolve())),
    ]
