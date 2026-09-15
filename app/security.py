"""Security and locality checks for the local-only runtime."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


@dataclass(frozen=True)
class SecurityFinding:
    name: str
    passed: bool
    detail: str


def validate_local_url(value: str) -> bool:
    """Return True only for loopback HTTP(S) URLs."""
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and parsed.hostname in LOCAL_HOSTS


def audit_tree(root: Path) -> list[SecurityFinding]:
    """Audit a storage tree for symlink escapes and unexpected secret-like files."""
    root = root.expanduser().resolve()
    findings: list[SecurityFinding] = []
    symlink_escapes = []
    secret_files = []
    secret_names = {".env", ".env.local", "credentials.json", "secrets.json"}
    for path in root.rglob("*"):
        if path.is_symlink():
            try:
                target = path.resolve()
                if target != root and root not in target.parents:
                    symlink_escapes.append(str(path))
            except OSError:
                symlink_escapes.append(str(path))
        if path.is_file() and path.name.lower() in secret_names:
            secret_files.append(str(path))
    findings.append(
        SecurityFinding(
            "symlink_containment",
            not symlink_escapes,
            "no storage symlink escapes found" if not symlink_escapes else "; ".join(symlink_escapes),
        )
    )
    findings.append(
        SecurityFinding(
            "secret_files",
            not secret_files,
            "no secret-like files found in storage" if not secret_files else "; ".join(secret_files),
        )
    )
    return findings


def local_only_findings(*urls: str) -> list[SecurityFinding]:
    """Audit configured service URLs against the loopback-only policy."""
    return [
        SecurityFinding("local_endpoint", validate_local_url(url), url) for url in urls
    ]
