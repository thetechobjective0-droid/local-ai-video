"""Application configuration with local-only defaults."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class RuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: str = "balanced"
    max_concurrent_media_jobs: int = Field(default=1, ge=1)
    local_only: bool = True


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = "ollama"
    model: str = "qwen2.5-coder:32b"
    temperature: float = Field(default=0.2, ge=0, le=2)
    top_p: float = Field(default=0.9, gt=0, le=1)
    top_k: int = Field(default=40, ge=1)


class StorageConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root: Path = Path("./data")


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runtime: RuntimeConfig = RuntimeConfig()
    llm: LLMConfig = LLMConfig()
    storage: StorageConfig = StorageConfig()


def load_config() -> AppConfig:
    """Return safe defaults for Phase 0; file-based loading is added next."""
    return AppConfig()
