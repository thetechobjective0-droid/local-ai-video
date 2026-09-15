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


def test_resolve_path_rejects_parent_traversal(tmp_path: Path) -> None:
    store = FilesystemStore(tmp_path, minimum_free_bytes=0)
    project = make_project()
    store.create_project(project)

    with pytest.raises(ValueError, match="escapes root"):
        store.project_path(project.id, Path("../outside.txt"))


def test_resolve_path_rejects_absolute_outside_path(tmp_path: Path) -> None:
    store = FilesystemStore(tmp_path, minimum_free_bytes=0)
    project = make_project()
    store.create_project(project)

    outside = tmp_path.parent / "outside.txt"
    with pytest.raises(ValueError, match="escapes root"):
        store.project_path(project.id, outside)


def test_resolve_path_rejects_symlink_escape(tmp_path: Path) -> None:
    store = FilesystemStore(tmp_path, minimum_free_bytes=0)
    project = make_project()
    directory = store.create_project(project)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    (directory / "linked").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="escapes root"):
        store.project_path(project.id, Path("linked/secret.txt"), must_exist=True)


def test_resolve_path_requires_existing_file(tmp_path: Path) -> None:
    store = FilesystemStore(tmp_path, minimum_free_bytes=0)
    project = make_project()
    store.create_project(project)

    with pytest.raises(FileNotFoundError):
        store.project_path(project.id, Path("missing.bin"), must_exist=True)
