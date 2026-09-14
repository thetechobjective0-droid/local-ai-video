"""Local provider adapters."""

from app.providers.diffusers_image import DiffusersImageProvider
from app.providers.ffmpeg_video import FFmpegVideoProvider
from app.providers.image import ImageGenerationRequest, ImageProvider, ImageResult
from app.providers.macos_tts import MacOSTTSProvider
from app.providers.ollama import OllamaProvider
from app.providers.tts import TTSProvider, TTSRequest, TTSResult
from app.providers.video import VideoGenerationRequest, VideoProvider, VideoResult

__all__ = [
    "DiffusersImageProvider",
    "FFmpegVideoProvider",
    "ImageGenerationRequest",
    "ImageProvider",
    "ImageResult",
    "MacOSTTSProvider",
    "OllamaProvider",
    "TTSProvider",
    "TTSRequest",
    "TTSResult",
    "VideoGenerationRequest",
    "VideoProvider",
    "VideoResult",
]
