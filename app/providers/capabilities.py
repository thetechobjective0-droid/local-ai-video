"""Central registry for deterministic local media-provider capabilities."""

from dataclasses import dataclass

from app.orchestrator.media_strategy import VideoCapability


@dataclass(frozen=True)
class ProviderCapabilities:
    """Capabilities exposed by one configured provider."""

    name: str
    video: VideoCapability


_PROVIDER_CAPABILITIES: dict[str, ProviderCapabilities] = {
    "ffmpeg_ken_burns": ProviderCapabilities(
        name="ffmpeg_ken_burns",
        video=VideoCapability(
            image_motion=True,
            image_to_video=False,
            text_to_video=False,
            max_duration_seconds=3600,
            memory_class="low",
        ),
    ),
    "ltx_video": ProviderCapabilities(
        name="ltx_video",
        video=VideoCapability(
            image_motion=False,
            image_to_video=True,
            text_to_video=False,
            max_duration_seconds=20,
            memory_class="high",
        ),
    ),
}


def get_provider_capabilities(provider_name: str) -> ProviderCapabilities:
    """Return capabilities for a supported local provider."""
    try:
        return _PROVIDER_CAPABILITIES[provider_name]
    except KeyError as exc:
        raise ValueError(f"unsupported local video provider: {provider_name}") from exc
