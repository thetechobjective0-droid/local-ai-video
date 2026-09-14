"""Versioned Director prompt templates."""

from pathlib import Path

PROMPT_VERSION = "v1"
PROMPT_ROOT = Path(__file__).resolve().parents[2] / "prompts" / "director" / PROMPT_VERSION


def load_prompt(name: str) -> str:
    """Load a checked-in prompt template by safe basename."""
    path = Path(name)
    if path.name != name or path.suffix != ".txt":
        raise ValueError("prompt name must be a .txt basename")
    return (PROMPT_ROOT / name).read_text(encoding="utf-8")
