"""Central construction of configured local media providers."""

from app.config import AppConfig
from app.exceptions import ConfigurationError
from app.providers.ffmpeg_video import FFmpegVideoProvider
from app.providers.ltx2_mlx_video import LTX2MLXVideoProvider
from app.providers.ltx_video import LTXVideoProvider
from app.providers.video import VideoProvider


def build_video_provider(config: AppConfig) -> VideoProvider:
    """Construct the configured local video provider in one place."""
    if not config.runtime.local_only:
        raise ConfigurationError("local_only must remain enabled")
    if config.video.provider == "ffmpeg_ken_burns":
        return FFmpegVideoProvider()
    if config.video.provider == "ltx2_mlx":
        return LTX2MLXVideoProvider(
            config.video.engine_path,
            config.video.model_path,
            uv_command=config.video.uv_command,
            low_ram=config.video.low_ram,
            pipeline=config.video.pipeline,
            native_audio=config.video.native_audio,
            i2v_strength=config.video.i2v_strength,
        )
    if config.video.provider == "ltx_video":
        if config.video.model_path is None:
            raise ConfigurationError("video.model_path is required for the local LTX provider")
        return LTXVideoProvider(
            config.video.model_path,
            device=config.video.device,
            dtype=config.video.dtype,
            inference_steps=config.video.inference_steps,
            guidance_scale=config.video.guidance_scale,
            guidance_rescale=config.video.guidance_rescale,
            image_cond_noise_scale=config.video.image_cond_noise_scale,
            decode_timestep=config.video.decode_timestep,
            decode_noise_scale=config.video.decode_noise_scale,
        )
    raise ConfigurationError(f"unsupported local video provider: {config.video.provider}")


def build_video_fallback(config: AppConfig) -> VideoProvider | None:
    """Return FFmpeg only when the operator explicitly enables fallback."""
    if config.video.provider == "ffmpeg_ken_burns" or not config.video.allow_fallback:
        return None
    return FFmpegVideoProvider()
