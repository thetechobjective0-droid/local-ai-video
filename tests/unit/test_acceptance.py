from pathlib import Path

from app.acceptance import AcceptanceCheck, AcceptanceReport, model_readiness


def test_model_readiness_rejects_missing_directory(tmp_path: Path) -> None:
    ok, detail = model_readiness(tmp_path / "missing")
    assert ok is False
    assert "does not exist" in detail


def test_model_readiness_requires_diffusers_metadata(tmp_path: Path) -> None:
    model = tmp_path / "model"
    model.mkdir()
    (model / "weights.safetensors").write_bytes(b"weights")

    ok, detail = model_readiness(model)

    assert ok is False
    assert "metadata" in detail


def test_model_readiness_reports_weights(tmp_path: Path) -> None:
    model = tmp_path / "model"
    model.mkdir()
    (model / "model_index.json").write_text("{}", encoding="utf-8")
    (model / "weights.safetensors").write_bytes(b"weights")

    ok, detail = model_readiness(model)

    assert ok is True
    assert "1 weight files" in detail


def test_acceptance_report_serializes_checks() -> None:
    report = AcceptanceReport(
        passed=True,
        platform="Darwin",
        machine="arm64",
        checks=(AcceptanceCheck("ffmpeg", True, "/usr/bin/ffmpeg"),),
        resource_before={
            "total_memory_bytes": 10,
            "available_memory_bytes": 8,
            "free_disk_bytes": 7,
        },
        resource_after={
            "total_memory_bytes": 10,
            "available_memory_bytes": 6,
            "free_disk_bytes": 6,
        },
    )

    payload = report.to_dict()

    assert payload["report_version"] == "1.0"
    assert payload["passed"] is True
    assert payload["checks"][0]["name"] == "ffmpeg"
