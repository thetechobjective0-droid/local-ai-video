"""Deterministic provider-fallback policy for local media generation."""

from dataclasses import dataclass

from app.exceptions import VideoAgentError
from app.providers.capabilities import get_provider_capabilities
from app.providers.video import VideoProvider


@dataclass(frozen=True)
class FallbackDecision:
    """Resolved fallback provider and its auditable reason."""

    provider: VideoProvider
    primary_provider: str
    fallback_provider: str
    reason: str


def resolve_video_fallback(
    primary: VideoProvider,
    fallback: VideoProvider | None,
    *,
    reason: str,
) -> FallbackDecision | None:
    """Accept only a distinct registered provider capable of image motion."""
    if fallback is None:
        return None
    primary_name = _provider_name(primary)
    fallback_name = _provider_name(fallback)
    if primary_name == fallback_name:
        raise VideoAgentError("video fallback provider must differ from the primary provider")
    try:
        capability = get_provider_capabilities(fallback_name).video
    except ValueError as exc:
        raise VideoAgentError(f"video fallback provider is not registered: {fallback_name}") from exc
    if not capability.image_motion:
        raise VideoAgentError(f"video fallback provider does not support image motion: {fallback_name}")
    return FallbackDecision(
        provider=fallback,
        primary_provider=primary_name,
        fallback_provider=fallback_name,
        reason=reason,
    )


def _provider_name(provider: VideoProvider) -> str:
    name = getattr(provider, "provider_name", None)
    if not isinstance(name, str) or not name:
        raise VideoAgentError("video provider does not expose a registered provider_name")
    return name
