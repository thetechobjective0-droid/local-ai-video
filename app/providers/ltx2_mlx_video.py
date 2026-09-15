"""Local LTX-2.3 MLX text/image-to-video provider for Apple Silicon."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.exceptions import ProviderUnavailableError, VideoAgentError
from app.providers.video import VideoGenerationRequest, VideoResult


class LTX2MLXVideoProvider:
    """Run the local LTX-2.3 MLX runtime through its offline CLI."""

    provider_name = "ltx2_mlx"
    model_name = "LTX-2.3-22B-MLX"

    def __init__(
        self,
        engine_path: Path,
        *,
        uv_command: str = "uv",
        bits: int = 8,
        native_audio: bool = True,
        i2v_strength: float = 0.95,
    ) -> None:
        self.engine_path = engine_path.expanduser().resolve()
        self.uv_command = uv_command
        self.bits = bits
        self.native_audio = native_audio
        self.i2v_strength = i2v_strength

    def generate(self, request: VideoGenerationRequest) -> VideoResult:
        if not request.image_path.is_file():
            raise VideoAgentError(f"Input image does not exist: {request.image_path}")
        if request.duration_seconds <= 0:
            raise ValueError("Video duration must be positive")
        if request.fps <= 0:
            raise ValueError("Video FPS must be positive")
        if not self.engine_path.is_dir():
            raise ProviderUnavailableError(
                f"LTX-2 MLX runtime directory does not exist: {self.engine_path}"
            )
        generate_script = self.engine_path / "generate.py"
        if not generate_script.is_file():
            raise ProviderUnavailableError(
                f"LTX-2 MLX runtime is missing generate.py: {generate_script}"
            )
        if self.bits not in {4, 8}:
            raise ValueError("LTX-2 MLX quantization bits must be 4 or 8")
        if not 0 <= self.i2v_strength <= 1:
            raise ValueError("LTX-2 MLX image conditioning strength must be between 0 and 1")

        frames = max(9, round(request.duration_seconds * request.fps))
        frames = ((frames - 1) // 8) * 8 + 1
        if frames < 41:
            frames = 41
        if frames > 241:
            raise VideoAgentError(
                "LTX-2 MLX scenes are limited to 10 seconds at the configured frame rate; "
                "reduce the scene duration or split the storyboard"
            )

        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        project_root = _project_root(request.metadata)
        temp_root = Path(
            tempfile.mkdtemp(prefix=".ltx2-", dir=str(request.output_path.parent))
        )
        try:
            prompt = request.prompt.strip() or "Natural cinematic motion with coherent temporal movement."
            command = [
                self.uv_command,
                "run",
                "--offline",
                "python",
                "generate.py",
                "--image",
                str(request.image_path),
                "--frames",
                str(frames),
                "--height",
                str(int(str(request.metadata.get("height", 512)))),
                "--width",
                str(int(str(request.metadata.get("width", 768)))),
                "--bits",
                str(self.bits),
                "--fps",
                str(request.fps),
                "--strength",
                str(self.i2v_strength),
                "--seed",
                str(request.seed if request.seed is not None else 0),
                "--output",
                str(temp_root),
                prompt,
            ]
            if not self.native_audio:
                command.insert(-2, "--no-audio")
            try:
                completed = subprocess.run(
                    command,
                    cwd=self.engine_path,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=max(900, round(request.duration_seconds * 300)),
                    env=_child_environment(),
                )
            except subprocess.TimeoutExpired as exc:
                raise ProviderUnavailableError("LTX-2 MLX generation timed out") from exc
            except OSError as exc:
                raise ProviderUnavailableError("uv/python could not start the LTX-2 MLX runtime") from exc
            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout).strip() or "unknown LTX-2 MLX error"
                raise VideoAgentError(f"LTX-2 MLX generation failed: {detail[-4000:]}")

            generated_video = _find_output(temp_root, "video.mp4")
            if generated_video is None:
                raise VideoAgentError("LTX-2 MLX runtime produced no video.mp4")
            shutil.copy2(generated_video, request.output_path)

            native_audio_path: Path | None = None
            generated_audio = _find_output(temp_root, "audio.wav")
            if self.native_audio and generated_audio is not None:
                audio_dir = project_root / "audio" if project_root else request.output_path.parent
                audio_dir.mkdir(parents=True, exist_ok=True)
                native_audio_path = audio_dir / f"scene-{int(str(request.metadata.get('scene_index', 0))):04d}-ltx2.wav"
                shutil.copy2(generated_audio, native_audio_path)

            digest = hashlib.sha256(request.output_path.read_bytes()).hexdigest()
            width = int(str(request.metadata.get("width", 768)))
            height = int(str(request.metadata.get("height", 512)))
            return VideoResult(
                path=request.output_path,
                provider=self.provider_name,
                model=self.model_name,
                duration_seconds=frames / request.fps,
                fps=request.fps,
                width=width,
                height=height,
                sha256=digest,
                metadata={
                    **request.metadata,
                    "generation_mode": "ai_i2v",
                    "video_generation_mode": "ai_i2v",
                    "temporal_generation": True,
                    "native_audio": bool(native_audio_path),
                    "native_audio_path": (
                        str(native_audio_path.relative_to(project_root))
                        if native_audio_path is not None and project_root is not None
                        else str(native_audio_path) if native_audio_path is not None else None
                    ),
                    "frame_count": frames,
                    "quantization_bits": self.bits,
                    "i2v_strength": self.i2v_strength,
                    "engine": "mlxc",
                },
            )
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)


def _find_output(root: Path, name: str) -> Path | None:
    matches = sorted(root.rglob(name))
    return matches[-1] if matches else None


def _project_root(metadata: dict[str, object]) -> Path | None:
    value = metadata.get("project_root")
    if not isinstance(value, str) or not value:
        return None
    return Path(value).expanduser().resolve()


def _child_environment() -> dict[str, str]:
    import os

    env = os.environ.copy()
    env.pop("MallocStackLogging", None)
    env.pop("MallocStackLoggingNoCompact", None)
    return env
