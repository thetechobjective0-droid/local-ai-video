"""Portable project archive export/import for V2."""

from __future__ import annotations

import shutil
from pathlib import Path
import tarfile
import tempfile
from uuid import UUID

from app.storage.filesystem import FilesystemStore
from app.storage.integrity import (
    build_integrity_manifest,
    verify_integrity_manifest,
    write_integrity_manifest,
)


ARCHIVE_VERSION = "1.0"


def _archive_root(store: FilesystemStore, project_id: UUID | str) -> Path:
    return store.project_dir(project_id)


def _manifest_files(root: Path) -> list[Path]:
    """Return deterministic archive files while excluding the manifest itself."""
    manifest = root / "integrity-manifest.json"
    return [path for path in root.rglob("*") if path.is_file() and path != manifest]


def export_project(store: FilesystemStore, project_id: UUID | str, destination: Path) -> Path:
    """Export a project directory as a portable tar.gz archive."""
    source = _archive_root(store, project_id)
    if not source.is_dir():
        raise FileNotFoundError(source)

    destination = destination.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="video-export-") as temp_dir:
        temp_root = Path(temp_dir) / source.name
        shutil.copytree(source, temp_root, symlinks=False)
        manifest = build_integrity_manifest(temp_root, _manifest_files(temp_root))
        write_integrity_manifest(temp_root / "integrity-manifest.json", manifest)
        marker = temp_root / "archive.json"
        marker.write_text(
            '{\n  "archive_version": "1.0",\n  "integrity_manifest": "integrity-manifest.json"\n}\n',
            encoding="utf-8",
        )
        manifest = build_integrity_manifest(temp_root, _manifest_files(temp_root))
        write_integrity_manifest(temp_root / "integrity-manifest.json", manifest)
        with tarfile.open(destination, "w:gz") as archive:
            archive.add(temp_root, arcname=source.name, recursive=True)
    return destination


def _safe_extract(archive: tarfile.TarFile, destination: Path) -> None:
    """Extract tar members safely on Python versions without TarFile filters."""
    for member in archive.getmembers():
        target = (destination / member.name).resolve()
        if target != destination and destination not in target.parents:
            raise ValueError("archive member escapes extraction root")
        if member.issym() or member.islnk():
            raise ValueError("archive links are not permitted")
        archive.extract(member, destination)


def import_project(store: FilesystemStore, archive_path: Path, project_id: UUID | str) -> Path:
    """Import a project archive after validating its manifest and containment."""
    archive_path = archive_path.expanduser().resolve()
    if not archive_path.is_file():
        raise FileNotFoundError(archive_path)
    destination = store.project_dir(project_id)
    if destination.exists():
        raise FileExistsError(destination)

    with tempfile.TemporaryDirectory(prefix="video-import-") as temp_dir:
        extraction = Path(temp_dir) / "extracted"
        extraction.mkdir()
        with tarfile.open(archive_path, "r:gz") as archive:
            _safe_extract(archive, extraction)
        roots = [item for item in extraction.iterdir() if item.is_dir()]
        if len(roots) != 1:
            raise ValueError("archive must contain exactly one project root")
        root = roots[0]
        manifest = root / "integrity-manifest.json"
        if not manifest.is_file():
            raise ValueError("project integrity manifest is missing")
        failures = verify_integrity_manifest(root, __import__("json").loads(manifest.read_text(encoding="utf-8")))
        if failures:
            raise ValueError("project integrity verification failed: " + "; ".join(failures))
        destination.parent.mkdir(parents=True, exist_ok=True)
        root.rename(destination)
    return destination
