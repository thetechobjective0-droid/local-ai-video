"""Application configuration with safe local-only defaults."""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class RuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile: str = Field(default="balanced", pattern="^(fast|balanced|quality)$")
    max_concurrent_media_jobs: int = Field(default=1, ge=1)
    local_only: bool = True


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str = "ollama"
    base_url: str = "http://127.0.0.1:11434"
    model: str = "qwen2.5-coder:32b"
    temperature: float = Field(default=0.2, ge=0, le=2)
    top_p: float = Field(default=0.9, gt=0, le=1)
    top_k: int = Field(default=40, ge=1)


class ImageConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str = "diffusers"
    model_path: Path = Path("./data/models/stable-diffusion-xl-base-1.0")
    device: str = Field(default="mps", pattern="^(mps|cpu)$")
    width: int = Field(default=1024, ge=64, multiple_of=8)
    height: int = Field(default=576, ge=64, multiple_of=8)
    steps: int = Field(default=30, ge=1, le=200)
    guidance_scale: float = Field(default=7.0, ge=0, le=30)


class TTSConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str = "macos_say"
    voice: str | None = None
    rate: int = Field(default=180, ge=1, le=600)
    sample_rate: int = Field(default=22050, ge=8000, le=48000)


class VideoConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # LTX-2.3 MLX is the production M4 path: temporal video plus native audio.
    # The older PyTorch LTX-Video provider remains available when explicitly selected.
    provider: str = "ltx2_mlx"
    model_path: Path | None = Path("./data/models/LTX-Video")
    engine_path: Path = Path("./data/runtime/ltx-video-mlx")
    uv_command: str = "uv"
    bits: int = Field(default=8, pattern="^[48]$")
    native_audio: bool = True
    i2v_strength: float = Field(default=0.95, ge=0, le=1)
    allow_fallback: bool = False
    device: str = Field(default="mps", pattern="^(mps|cpu)$")
    dtype: str = Field(default="float16", pattern="^(float16|bfloat16|float32)$")
    width: int = Field(default=768, ge=64, multiple_of=32)
    height: int = Field(default=512, ge=64, multiple_of=32)
    fps: int = Field(default=25, ge=1, le=60)
    inference_steps: int = Field(default=8, ge=1, le=100)
    guidance_scale: float = Field(default=1.0, ge=0, le=20)
    guidance_rescale: float = Field(default=0.0, ge=0, le=1)
    image_cond_noise_scale: float = Field(default=0.025, ge=0, le=1)
    decode_timestep: float = Field(default=0.05, ge=0, le=1)
    decode_noise_scale: float | None = Field(default=0.025, ge=0, le=1)


class StorageConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    root: Path = Path("./data")


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    runtime: RuntimeConfig = RuntimeConfig()
    llm: LLMConfig = LLMConfig()
    image: ImageConfig = ImageConfig()
    tts: TTSConfig = TTSConfig()
    video: VideoConfig = VideoConfig()
    storage: StorageConfig = StorageConfig()


def load_config(path: Path | None = None) -> AppConfig:
    """Load YAML configuration, falling back to safe local AI-video defaults."""
    if path is None:
        return AppConfig()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return AppConfig.model_validate(data)
