from pathlib import Path

import pytest

from app.exceptions import InsufficientDiskError
from app.models.project import VideoProject
from app.storage.filesystem import FilesystemStore


def make_project() -> VideoProject:
    return VideoProject(source_prompt="test video", duration_seconds=10)


def test_project_round_trip(tmp_path: Path) -> None:
    store = FilesystemStore(tmp_path, minimum_free_bytes=0)
    project = make_project()
    directory = store.create_project(project)

    loaded = store.load_project(project.id)

    assert directory == tmp_path.resolve() / "projects" / str(project.id)
    assert loaded.id == project.id
    assert loaded.source_prompt == project.source_prompt


def test_project_directory_is_below_root(tmp_path: Path) -> None:
    store = FilesystemStore(tmp_path, minimum_free_bytes=0)
    path = store.project_dir("abc")
    assert tmp_path.resolve() in path.parents


def test_low_disk_space_is_rejected(tmp_path: Path) -> None:
    store = FilesystemStore(tmp_path, minimum_free_bytes=10**30)
    with pytest.raises(InsufficientDiskError):
        store.ensure_capacity()
