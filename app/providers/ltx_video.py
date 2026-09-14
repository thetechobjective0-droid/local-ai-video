"""Local LTX-Video image-to-video provider using Diffusers."""

import hashlib
from pathlib import Path
from typing import Any

from app.exceptions import ProviderUnavailableError, VideoAgentError
from app.providers.video import VideoGenerationRequest, VideoResult


class LTXVideoProvider:
    """Run a locally stored LTX-Video checkpoint through Diffusers on MPS/CPU."""

    provider_name = "ltx_video"

    def __init__(
        self,
        model_path: Path,
        *,
        device: str = "mps",
        dtype: str = "float16",
    ) -> None:
        self.model_path = model_path.expanduser().resolve()
        self.device = device
        self.dtype = dtype
        self._pipeline: Any = None
        self._model_name = self.model_path.name

    def _load_pipeline(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline
        if not self.model_path.is_dir():
            raise ProviderUnavailableError(f"LTX model directory does not exist: {self.model_path}")
        try:
            import torch
            from diffusers import DiffusionPipeline
        except ImportError as exc:
            raise ProviderUnavailableError(
                "LTX video dependencies are unavailable; install the image/video dependencies"
            ) from exc

        dtype = getattr(torch, self.dtype, None)
        if dtype is None:
            raise ValueError(f"unsupported torch dtype: {self.dtype}")
        try:
            pipeline = DiffusionPipeline.from_pretrained(
                self.model_path,
                torch_dtype=dtype,
                local_files_only=True,
            )
            pipeline.to(self.device)
        except Exception as exc:
            raise ProviderUnavailableError("failed to load the local LTX video model") from exc
        self._pipeline = pipeline
        return pipeline

    def generate(self, request: VideoGenerationRequest) -> VideoResult:
        if not request.image_path.is_file():
            raise VideoAgentError(f"Input image does not exist: {request.image_path}")
        if request.duration_seconds <= 0:
            raise ValueError("Video duration must be positive")
        if request.fps <= 0:
            raise ValueError("Video FPS must be positive")
        if request.seed is not None and request.seed < 0:
            raise ValueError("Video seed must be non-negative")

        frames = max(9, round(request.duration_seconds * request.fps))
        frames = ((frames - 1) // 8) * 8 + 1
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        pipeline = self._load_pipeline()
        try:
            from diffusers.utils import export_to_video, load_image
            import torch

            generator = None
            if request.seed is not None:
                generator = torch.Generator(device="cpu").manual_seed(request.seed)
            image = load_image(str(request.image_path))
            result = pipeline(
                image=image,
                prompt=request.prompt,
                width=request.metadata.get("width", 704),
                height=request.metadata.get("height", 384),
                num_frames=frames,
                generator=generator,
            )
            frames_output = result.frames[0]
            export_to_video(frames_output, str(request.output_path), fps=request.fps)
        except (OSError, RuntimeError, ValueError) as exc:
            raise VideoAgentError("LTX image-to-video generation failed") from exc
        except Exception as exc:
            raise VideoAgentError("LTX image-to-video generation failed") from exc

        if not request.output_path.is_file() or request.output_path.stat().st_size == 0:
            raise VideoAgentError("LTX returned no usable video file")
        digest = hashlib.sha256(request.output_path.read_bytes()).hexdigest()
        width = int(request.metadata.get("width", 704))
        height = int(request.metadata.get("height", 384))
        duration = frames / request.fps
        return VideoResult(
            path=request.output_path,
            provider=self.provider_name,
            model=self._model_name,
            duration_seconds=duration,
            fps=request.fps,
            width=width,
            height=height,
            sha256=digest,
            metadata={
                **request.metadata,
                "num_frames": frames,
                "device": self.device,
                "dtype": self.dtype,
            },
        )
