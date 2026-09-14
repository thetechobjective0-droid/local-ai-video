"""Local runtime health and preflight checks."""

from dataclasses import dataclass
import platform
import shutil


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


def check_command(name: str) -> CheckResult:
    path = shutil.which(name)
    return CheckResult(name, path is not None, path or "not found")


def run_health_checks() -> list[CheckResult]:
    """Run dependency checks without invoking remote services."""
    return [check_platform(), check_command("ffmpeg"), check_command("ollama")]
