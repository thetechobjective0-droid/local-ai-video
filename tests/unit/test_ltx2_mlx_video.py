from pathlib import Path

from app.providers.ltx2_mlx_video import LTX2MLXVideoProvider
from app.providers.video import VideoGenerationRequest


def test_ltx2_mlx_provider_builds_offline_i2v_command(tmp_path, monkeypatch) -> None:
    engine = tmp_path / "runtime"
    engine.mkdir()
    model = tmp_path / "model"
    model.mkdir()
    image = tmp_path / "image.png"
    image.write_bytes(b"image")
    output = tmp_path / "videos" / "scene-0001.mp4"
    project = tmp_path / "project"
    project.mkdir()

    captured: list[list[str]] = []

    class Result:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(command, **kwargs):
        captured.append(command)
        if command[0] == "uv":
            generated = Path(command[command.index("--output") + 1])
            generated.parent.mkdir(parents=True, exist_ok=True)
            generated.write_bytes(b"video")
        else:
            audio = Path(command[-1])
            audio.parent.mkdir(parents=True, exist_ok=True)
            audio.write_bytes(b"audio")
        return Result()

    monkeypatch.setattr("app.providers.ltx2_mlx_video.subprocess.run", fake_run)

    result = LTX2MLXVideoProvider(engine, model).generate(
        VideoGenerationRequest(
            image_path=image,
            output_path=output,
            prompt="a cat drives a car and sings",
            duration_seconds=5,
            fps=24,
            seed=7,
            metadata={
                "project_root": str(project),
                "scene_index": 1,
                "width": 704,
                "height": 480,
            },
        )
    )

    generation_command = captured[0]
    assert generation_command[:4] == ["uv", "run", "--offline", "ltx-2-mlx"]
    assert "generate" in generation_command
    assert "--image" in generation_command
    assert "--model" in generation_command
    assert "--two-stage" in generation_command
    assert "--low-ram" in generation_command
    assert result.provider == "ltx2_mlx"
    assert result.metadata["generation_mode"] == "ai_i2v"
    assert result.metadata["temporal_generation"] is True
    assert result.metadata["native_audio"] is True
    assert output.is_file()
