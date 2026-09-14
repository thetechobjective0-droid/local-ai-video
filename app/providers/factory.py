"""Central construction of configured local media providers."""

from app.config import AppConfig
from app.exceptions import ConfigurationError
from app.providers.ffmpeg_video import FFmpegVideoProvider
from app.providers.ltx_video import LTXVideoProvider
from app.providers.video import VideoProvider


def build_video_provider(config: AppConfig) -> VideoProvider:
    """Construct the configured local video provider in one place."""
    if not config.runtime.local_only:
        raise ConfigurationError("local_only must remain enabled")
    if config.video.provider == "ffmpeg_ken_burns":
        return FFmpegVideoProvider()
    if config.video.provider == "ltx_video":
        if config.video.model_path is None:
            raise ConfigurationError("video.model_path is required for the local LTX provider")
        return LTXVideoProvider(
            config.video.model_path,
            device=config.video.device,
            dtype=config.video.dtype,
        )
    raise ConfigurationError(f"unsupported local video provider: {config.video.provider}")


def build_video_fallback(config: AppConfig) -> VideoProvider | None:
    """Return the deterministic fallback when the primary provider is not FFmpeg."""
    if config.video.provider == "ffmpeg_ken_burns":
        return None
    return FFmpegVideoProvider()
