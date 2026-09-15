from pathlib import Path

from app.providers.ltx2_mlx_video import LTX2MLXVideoProvider
from app.providers.video import VideoGenerationRequest


def test_ltx2_mlx_provider_builds_offline_i2v_command(tmp_path, monkeypatch) -> None:
    engine = tmp_path / "runtime"
    engine.mkdir()
    (engine / "generate.py").write_text("# stub\n", encoding="utf-8")
    image = tmp_path / "image.png"
    image.write_bytes(b"image")
    output = tmp_path / "videos" / "scene-0001.mp4"
    project = tmp_path / "project"
    project.mkdir()

    captured: dict[str, object] = {}

    class Result:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(command, **kwargs):
        captured["command"] = command
        output_root = Path(command[command.index("--output") + 1])
        generated = output_root / "2026-01-01-000000"
        generated.mkdir(parents=True)
        (generated / "video.mp4").write_bytes(b"video")
        (generated / "audio.wav").write_bytes(b"audio")
        return Result()

    monkeypatch.setattr("app.providers.ltx2_mlx_video.subprocess.run", fake_run)

    result = LTX2MLXVideoProvider(engine).generate(
        VideoGenerationRequest(
            image_path=image,
            output_path=output,
            prompt="a cat drives a car and sings",
            duration_seconds=5,
            fps=25,
            seed=7,
            metadata={
                "project_root": str(project),
                "scene_index": 1,
                "width": 768,
                "height": 512,
            },
        )
    )

    command = captured["command"]
    assert isinstance(command, list)
    assert command[:4] == ["uv", "run", "--offline", "python"]
    assert "--image" in command
    assert "--frames" in command
    assert "--bits" in command
    assert "--no-audio" not in command
    assert result.provider == "ltx2_mlx"
    assert result.metadata["generation_mode"] == "ai_i2v"
    assert result.metadata["temporal_generation"] is True
    assert result.metadata["native_audio"] is True
    assert output.is_file()
    assert (project / "audio" / "scene-0001-ltx2.wav").is_file()
