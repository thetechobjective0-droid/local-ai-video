"""Local provider adapters."""

from app.providers.diffusers_image import DiffusersImageProvider
from app.providers.image import ImageGenerationRequest, ImageProvider, ImageResult
from app.providers.ollama import OllamaProvider

__all__ = [
    "DiffusersImageProvider",
    "ImageGenerationRequest",
    "ImageProvider",
    "ImageResult",
    "OllamaProvider",
]
