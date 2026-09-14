"""Local provider adapters."""

from app.providers.image import ImageGenerationRequest, ImageProvider, ImageResult
from app.providers.ollama import OllamaProvider

__all__ = [
    "ImageGenerationRequest",
    "ImageProvider",
    "ImageResult",
    "OllamaProvider",
]
