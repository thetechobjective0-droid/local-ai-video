from pathlib import Path

from app.preflight import _memory_bytes, memory_gib, snapshot


def test_snapshot_reports_positive_resources(tmp_path: Path) -> None:
    result = snapshot(tmp_path)
    assert result.total_memory_bytes > 0
    assert result.available_memory_bytes > 0
    assert result.free_disk_bytes > 0


def test_memory_gib_conversion() -> None:
    assert memory_gib(1024**3) == 1.0


def test_memory_bytes_reports_valid_range() -> None:
    total, available = _memory_bytes()
    assert total > 0
    assert 0 <= available <= total
