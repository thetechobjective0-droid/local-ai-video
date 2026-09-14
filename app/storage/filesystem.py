"""Safe filesystem-backed project storage."""

from pathlib import Path
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

    def ensure_capacity(self, required_bytes: int = 0) -> None:
        """Fail before generation if free space is below the configured safety floor."""
        usage = self.root.stat().st_dev
        del usage
        free_bytes = __import__("shutil").disk_usage(self.root).free
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
        (directory / "project.json").write_text(
            project.model_dump_json(indent=2), encoding="utf-8"
        )
        return directory

    def load_project(self, project_id: UUID | str) -> VideoProject:
        """Load and validate project metadata from disk."""
        path = self.project_dir(project_id) / "project.json"
        return VideoProject.model_validate_json(path.read_text(encoding="utf-8"))
