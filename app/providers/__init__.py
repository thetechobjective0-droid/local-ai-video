"""Local provider adapters."""

from app.providers.diffusers_image import DiffusersImageProvider
from app.providers.image import ImageGenerationRequest, ImageProvider, ImageResult
from app.providers.macos_tts import MacOSTTSProvider
from app.providers.ollama import OllamaProvider
from app.providers.tts import TTSProvider, TTSRequest, TTSResult

__all__ = [
    "DiffusersImageProvider",
    "ImageGenerationRequest",
    "ImageProvider",
    "ImageResult",
    "MacOSTTSProvider",
    "OllamaProvider",
    "TTSProvider",
    "TTSRequest",
    "TTSResult",
]
