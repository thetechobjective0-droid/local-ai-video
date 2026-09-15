"""Local LTX-Video image-to-video provider using Diffusers."""

from __future__ import annotations

import gc
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
        inference_steps: int = 40,
        guidance_scale: float = 3.0,
        guidance_rescale: float = 0.0,
        image_cond_noise_scale: float = 0.025,
        decode_timestep: float = 0.05,
        decode_noise_scale: float | None = 0.025,
    ) -> None:
        self.model_path = model_path.expanduser().resolve()
        self.device = device
        self.dtype = dtype
        self.inference_steps = inference_steps
        self.guidance_scale = guidance_scale
        self.guidance_rescale = guidance_rescale
        self.image_cond_noise_scale = image_cond_noise_scale
        self.decode_timestep = decode_timestep
        self.decode_noise_scale = decode_noise_scale
        self._pipeline: Any = None
        self._model_name = self.model_path.name

    def _load_pipeline(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline
        if not self.model_path.is_dir():
            raise ProviderUnavailableError(f"LTX model directory does not exist: {self.model_path}")
        try:
            import torch
            from diffusers import LTXImageToVideoPipeline
        except ImportError as exc:
            raise ProviderUnavailableError(
                "LTX video dependencies are unavailable; install the image/video dependencies"
            ) from exc

        dtype = getattr(torch, self.dtype, None)
        if dtype is None:
            raise ValueError(f"unsupported torch dtype: {self.dtype}")
        try:
            pipeline = LTXImageToVideoPipeline.from_pretrained(
                self.model_path,
                torch_dtype=dtype,
                local_files_only=True,
            )
            pipeline.to(self.device)
            if hasattr(pipeline, "enable_attention_slicing"):
                pipeline.enable_attention_slicing("auto")
            if hasattr(pipeline, "enable_vae_slicing"):
                pipeline.enable_vae_slicing()
            if hasattr(pipeline, "enable_vae_tiling"):
                pipeline.enable_vae_tiling()
        except Exception as exc:
            raise ProviderUnavailableError("failed to load the local LTX video model") from exc
        self._pipeline = pipeline
        return pipeline

    @staticmethod
    def _release_torch_memory() -> None:
        """Release temporary tensors and opportunistically return accelerator cache."""
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
        except (ImportError, AttributeError, RuntimeError):
            pass

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
        metadata = request.metadata
        inference_steps = self.inference_steps
        guidance_scale = self.guidance_scale
        guidance_rescale = self.guidance_rescale
        image_cond_noise_scale = self.image_cond_noise_scale
        decode_timestep = self.decode_timestep
        decode_noise_scale = self.decode_noise_scale
        prompt = request.prompt.strip()
        negative_prompt = request.negative_prompt.strip() or (
            "worst quality, low quality, blurry, jittery, flicker, inconsistent motion, "
            "warping, morphing, duplicate subjects, deformed anatomy, unstable geometry, "
            "camera shake, abrupt zoom, text, watermark"
        )
        if not prompt:
            prompt = "Smooth cinematic natural motion, preserve the subject identity and composition."

        try:
            from diffusers.utils import export_to_video, load_image
            import torch

            generator = None
            if request.seed is not None:
                generator = torch.Generator(device="cpu").manual_seed(request.seed)
            call_kwargs: dict[str, object] = {
                "image": load_image(str(request.image_path)),
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": int(str(metadata.get("width", 704))),
                "height": int(str(metadata.get("height", 480))),
                "num_frames": frames,
                "frame_rate": request.fps,
                "num_inference_steps": inference_steps,
                "guidance_scale": guidance_scale,
                "guidance_rescale": guidance_rescale,
                "image_cond_noise_scale": image_cond_noise_scale,
                "generator": generator,
            }
            if decode_timestep > 0:
                call_kwargs["decode_timestep"] = decode_timestep
            if decode_noise_scale is not None:
                call_kwargs["decode_noise_scale"] = decode_noise_scale
            with torch.inference_mode():
                result = pipeline(**call_kwargs)
                frames_output = result.frames[0]
                export_to_video(frames_output, str(request.output_path), fps=request.fps)
                del frames_output, result, call_kwargs, generator
        except TypeError:
            # Keep compatibility with older local Diffusers releases that do not
            # expose the timestep-aware optional arguments.
            try:
                import torch
                from diffusers.utils import export_to_video, load_image

                generator = (
                    torch.Generator(device="cpu").manual_seed(request.seed)
                    if request.seed is not None
                    else None
                )
                with torch.inference_mode():
                    result = pipeline(
                        image=load_image(str(request.image_path)),
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        width=int(str(metadata.get("width", 704))),
                        height=int(str(metadata.get("height", 480))),
                        num_frames=frames,
                        frame_rate=request.fps,
                        num_inference_steps=inference_steps,
                        guidance_scale=guidance_scale,
                        generator=generator,
                    )
                    frames_output = result.frames[0]
                    export_to_video(frames_output, str(request.output_path), fps=request.fps)
                    del frames_output, result, generator
            except Exception as exc:
                raise VideoAgentError("LTX image-to-video generation failed") from exc
        except (OSError, RuntimeError, ValueError) as exc:
            raise VideoAgentError("LTX image-to-video generation failed") from exc
        except Exception as exc:
            raise VideoAgentError("LTX image-to-video generation failed") from exc
        finally:
            self._release_torch_memory()

        if not request.output_path.is_file() or request.output_path.stat().st_size == 0:
            raise VideoAgentError("LTX returned no usable video file")
        digest = hashlib.sha256(request.output_path.read_bytes()).hexdigest()
        width = int(str(metadata.get("width", 704)))
        height = int(str(metadata.get("height", 480)))
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
                **metadata,
                "generation_mode": "ai_i2v",
                "temporal_generation": True,
                "num_frames": frames,
                "effective_prompt": prompt,
                "negative_prompt": negative_prompt,
                "inference_steps": inference_steps,
                "guidance_scale": guidance_scale,
                "guidance_rescale": guidance_rescale,
                "image_cond_noise_scale": image_cond_noise_scale,
                "decode_timestep": decode_timestep,
                "decode_noise_scale": decode_noise_scale,
                "device": self.device,
                "dtype": self.dtype,
            },
        )
