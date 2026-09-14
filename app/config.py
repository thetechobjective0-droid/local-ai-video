"""Application configuration with safe local-only defaults."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
import yaml


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


class StorageConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    root: Path = Path("./data")


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    runtime: RuntimeConfig = RuntimeConfig()
    llm: LLMConfig = LLMConfig()
    image: ImageConfig = ImageConfig()
    storage: StorageConfig = StorageConfig()


def load_config(path: Path | None = None) -> AppConfig:
    """Load YAML configuration, falling back to safe defaults."""
    if path is None:
        return AppConfig()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return AppConfig.model_validate(data)
