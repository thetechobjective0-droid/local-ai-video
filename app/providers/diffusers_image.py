"""Apple-Silicon-friendly local Diffusers text-to-image backend."""

from __future__ import annotations

import hashlib
from pathlib import Path
from time import monotonic

from app.exceptions import ProviderUnavailableError, VideoAgentError
from app.providers.image import ImageGenerationRequest, ImageResult


class DiffusersImageProvider:
    """Run a locally cached Diffusers text-to-image model on Apple Silicon MPS."""

    provider_name = "diffusers"

    def __init__(self, model_path: Path, *, device: str = "mps") -> None:
        self.model_path = model_path.expanduser().resolve()
        self.device = device
        if not self.model_path.is_dir():
            raise ProviderUnavailableError(
                f"local image model directory does not exist: {self.model_path}"
            )
        if device not in {"mps", "cpu"}:
            raise ValueError("image device must be 'mps' or 'cpu'")

    def _load_pipeline(self) -> object:
        try:
            import torch
            from diffusers import AutoPipelineForText2Image
        except ImportError as exc:
            raise ProviderUnavailableError(
                "Diffusers image support requires the image optional dependencies"
            ) from exc

        if self.device == "mps" and not torch.backends.mps.is_available():
            raise ProviderUnavailableError("PyTorch MPS is not available on this machine")

        dtype = torch.float16 if self.device == "mps" else torch.float32
        pipeline = AutoPipelineForText2Image.from_pretrained(
            self.model_path,
            torch_dtype=dtype,
            local_files_only=True,
            use_safetensors=True,
        )
        pipeline = pipeline.to(self.device)
        return pipeline

    def generate(self, request: ImageGenerationRequest) -> ImageResult:
        if not request.prompt.strip():
            raise ValueError("image prompt must not be empty")
        if request.width < 64 or request.height < 64:
            raise ValueError("image dimensions must be at least 64 pixels")
        if request.width % 8 or request.height % 8:
            raise ValueError("image dimensions must be divisible by 8")
        if request.steps < 1 or request.steps > 200:
            raise ValueError("image steps must be between 1 and 200")
        if request.guidance_scale < 0 or request.guidance_scale > 30:
            raise ValueError("guidance scale must be between 0 and 30")

        output = request.output_path.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.suffix.lower() != ".png":
            raise ValueError("image output must use the .png extension")

        pipeline = self._load_pipeline()
        start = monotonic()
        try:
            import torch

            generator = None
            if request.seed is not None:
                generator = torch.Generator(device="cpu").manual_seed(request.seed)
            result = pipeline(
                prompt=request.prompt,
                negative_prompt=request.negative_prompt or None,
                width=request.width,
                height=request.height,
                num_inference_steps=request.steps,
                guidance_scale=request.guidance_scale,
                generator=generator,
            )
            image = result.images[0]
            image.save(output, format="PNG")
        except Exception as exc:
            raise VideoAgentError(f"local image generation failed: {exc}") from exc

        if not output.is_file() or output.stat().st_size == 0:
            raise VideoAgentError("image provider produced an empty output")

        digest = hashlib.sha256(output.read_bytes()).hexdigest()
        return ImageResult(
            path=output,
            model=self.model_path.name,
            provider=self.provider_name,
            width=request.width,
            height=request.height,
            seed=request.seed,
            sha256=digest,
            metadata={
                "steps": request.steps,
                "guidance_scale": request.guidance_scale,
                "generation_seconds": round(monotonic() - start, 3),
                **request.metadata,
            },
        )
