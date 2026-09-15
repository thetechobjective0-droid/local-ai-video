"""Versioned local provider registry and compatibility discovery."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.orchestrator.media_strategy import VideoCapability
from app.providers.capabilities import get_provider_capabilities


@dataclass(frozen=True)
class ProviderDescriptor:
    name: str
    version: str
    kind: str
    capabilities: dict[str, object]
    local_only: bool = True


_REGISTRY: dict[str, ProviderDescriptor] = {
    "ffmpeg_ken_burns": ProviderDescriptor(
        name="ffmpeg_ken_burns", version="1.0", kind="video", capabilities=asdict(get_provider_capabilities("ffmpeg_ken_burns").video)
    ),
    "ltx_video": ProviderDescriptor(
        name="ltx_video", version="1.0", kind="video", capabilities=asdict(get_provider_capabilities("ltx_video").video)
    ),
    "macos_tts": ProviderDescriptor(name="macos_tts", version="1.0", kind="audio", capabilities={"platform": "darwin"}),
    "ollama": ProviderDescriptor(name="ollama", version="1.0", kind="llm", capabilities={"structured_output": True}),
}


def list_providers() -> list[ProviderDescriptor]:
    return sorted(_REGISTRY.values(), key=lambda item: (item.kind, item.name))


def provider(name: str) -> ProviderDescriptor:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"unknown local provider: {name}") from exc


def compatible_video_providers(capability: VideoCapability) -> list[ProviderDescriptor]:
    result: list[ProviderDescriptor] = []
    for descriptor in list_providers():
        if descriptor.kind != "video":
            continue
        values = descriptor.capabilities
        if capability.image_to_video and not values.get("image_to_video", False):
            continue
        if capability.text_to_video and not values.get("text_to_video", False):
            continue
        result.append(descriptor)
    return result
