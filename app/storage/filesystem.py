"""Safe filesystem-backed project storage."""

import json
from pathlib import Path
import shutil
import tempfile
from typing import Any
from uuid import UUID

from app.exceptions import InsufficientDiskError
from app.models.project import VideoProject


class FilesystemStore:
    """Store project metadata below one configured root directory."""

    def __init__(self, root: Path, *, minimum_free_bytes: int = 512 * 1024 * 1024) -> None:
        self.root = root.expanduser().resolve()
        self.minimum_free_bytes = minimum_free_bytes
        self.root.mkdir(parents=True, exist_ok=True)

    def project_dir(self, project_id: UUID | str) -> Path:
        """Return a validated project directory beneath the storage root."""
        candidate = (self.root / "projects" / str(project_id)).resolve()
        if self.root not in candidate.parents:
            raise ValueError("project path escapes storage root")
        return candidate

    @staticmethod
    def resolve_path(root: Path, path: Path, *, must_exist: bool = False) -> Path:
        """Resolve a path beneath root, rejecting traversal and symlink escapes."""
        root = root.expanduser().resolve()
        candidate = path.expanduser()
        resolved = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError(f"path escapes root: {path}")
        if must_exist and not resolved.is_file():
            raise FileNotFoundError(resolved)
        return resolved

    def project_path(self, project_id: UUID | str, path: Path, *, must_exist: bool = False) -> Path:
        """Resolve a project-relative path while following and validating symlinks."""
        return self.resolve_path(self.project_dir(project_id), path, must_exist=must_exist)

    def ensure_capacity(self, required_bytes: int = 0) -> None:
        """Fail before generation if free space is below the configured safety floor."""
        free_bytes = shutil.disk_usage(self.root).free
        if free_bytes < self.minimum_free_bytes + required_bytes:
            raise InsufficientDiskError(
                f"insufficient disk space: {free_bytes} bytes free, "
                f"{required_bytes + self.minimum_free_bytes} bytes required"
            )

    def create_project(self, project: VideoProject) -> Path:
        """Create a project directory and persist its canonical JSON metadata."""
        self.ensure_capacity()
        directory = self.project_dir(project.id)
        directory.mkdir(parents=True, exist_ok=False)
        self.write_json(directory, "project.json", project.model_dump(mode="json"))
        return directory

    def write_json(self, directory: Path, filename: str, value: Any) -> Path:
        """Atomically persist a JSON artifact inside an existing project directory."""
        directory = directory.resolve()
        target = self.resolve_path(directory, Path(filename))
        if not filename or Path(filename).name != filename or Path(filename).suffix != ".json":
            raise ValueError("artifact filename must be a single .json basename")

        payload = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=directory, prefix=".tmp-", delete=False
        ) as temp:
            temp.write(payload)
            temp_path = Path(temp.name)
        temp_path.replace(target)
        return target

    def load_project(self, project_id: UUID | str) -> VideoProject:
        """Load and validate project metadata from disk."""
        path = self.project_path(project_id, Path("project.json"), must_exist=True)
        return VideoProject.model_validate_json(path.read_text(encoding="utf-8"))
