from pathlib import Path

from app.security import audit_tree, validate_local_url


def test_validate_local_url_rejects_remote_hosts() -> None:
    assert validate_local_url("http://127.0.0.1:11434")
    assert validate_local_url("https://localhost:8443")
    assert not validate_local_url("https://example.com")
    assert not validate_local_url("file:///tmp/model")


def test_audit_tree_detects_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "data"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "escape").symlink_to(outside, target_is_directory=True)

    findings = audit_tree(root)

    containment = next(item for item in findings if item.name == "symlink_containment")
    assert containment.passed is False
