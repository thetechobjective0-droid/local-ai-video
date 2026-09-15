from pathlib import Path

from fastapi.testclient import TestClient

from app.storage.filesystem import FilesystemStore
from app.web import app


def test_web_server_is_loopback_only() -> None:
    source = Path("app/web.py").read_text(encoding="utf-8")
    assert 'uvicorn.run(app, host="127.0.0.1", port=8765)' in source


def test_health_reports_local_only() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mode": "local-only"}


def test_project_path_rejects_symlinked_directory_escape(tmp_path: Path) -> None:
    store = FilesystemStore(tmp_path, minimum_free_bytes=0)
    project_dir = store.project_dir("security-test")
    project_dir.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "payload.bin").write_bytes(b"payload")
    (project_dir / "assets").symlink_to(outside, target_is_directory=True)

    try:
        store.project_path("security-test", Path("assets/payload.bin"), must_exist=True)
    except ValueError as exc:
        assert "escapes root" in str(exc)
    else:
        raise AssertionError("symlink escape was not rejected")
