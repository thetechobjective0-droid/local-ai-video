"""Local artifact integrity manifests for reproducible V2 projects."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


CHUNK_SIZE = 1024 * 1024


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a local file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_integrity_manifest(root: Path, files: list[Path]) -> dict[str, Any]:
    """Build a deterministic relative-path/size/digest manifest beneath root."""
    root = root.expanduser().resolve()
    entries: list[dict[str, Any]] = []
    for path in sorted(files, key=lambda item: str(item)):
        resolved = path.expanduser().resolve()
        if root not in resolved.parents:
            raise ValueError(f"artifact escapes root: {path}")
        if not resolved.is_file():
            raise FileNotFoundError(resolved)
        entries.append(
            {
                "path": resolved.relative_to(root).as_posix(),
                "size": resolved.stat().st_size,
                "sha256": sha256_file(resolved),
            }
        )
    return {"manifest_version": "1.0", "files": entries}


def write_integrity_manifest(path: Path, manifest: dict[str, Any]) -> Path:
    """Atomically persist an integrity manifest."""
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)
    return path


def verify_integrity_manifest(root: Path, manifest: dict[str, Any]) -> list[str]:
    """Return integrity failures; an empty list means the manifest verifies."""
    root = root.expanduser().resolve()
    failures: list[str] = []
    for entry in manifest.get("files", []):
        relative = Path(str(entry["path"]))
        try:
            resolved = (root / relative).resolve()
            if root not in resolved.parents:
                failures.append(f"path escapes root: {relative}")
                continue
            if not resolved.is_file():
                failures.append(f"missing file: {relative}")
                continue
            if resolved.stat().st_size != int(entry["size"]):
                failures.append(f"size mismatch: {relative}")
                continue
            if sha256_file(resolved) != str(entry["sha256"]):
                failures.append(f"sha256 mismatch: {relative}")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            failures.append(f"verification error for {relative}: {exc}")
    return failures
