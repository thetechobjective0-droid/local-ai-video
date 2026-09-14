# Phase 3 — Local Image Generation Status

Phase 3 code implementation is complete pending real M4 model acceptance.

## Implemented

- Provider-agnostic `ImageProvider` protocol.
- Typed `ImageGenerationRequest` and `ImageResult` contracts.
- Local Diffusers text-to-image backend.
- Apple Silicon MPS execution path.
- CPU fallback for environments without MPS.
- `local_files_only=True` model loading; generation never downloads model weights.
- Prompt and negative-prompt propagation.
- Configurable width, height, inference steps, guidance scale, and seed.
- PNG output validation.
- SHA-256 integrity validation at the generation-service boundary.
- Artifact metadata containing provider, model, parameters, scene ID, and output hash.
- Independent scene image generation service.
- `video-agent generate-scene <project-id> <scene-id>` CLI command.
- Optional `image` dependency group for Diffusers/PyTorch/Pillow/SafeTensors/Transformers.
- CI-safe unit tests using a fake image provider; heavyweight model dependencies are not required by the default CI quality job.

## Local M4 acceptance

A real M4 run must provide a pre-downloaded Diffusers-compatible model under the configured `image.model_path`, install the image optional dependencies, and generate at least one storyboard scene. Measure generation latency, memory pressure, output dimensions, and artifact integrity before selecting the default model/profile permanently.

## Boundary

Phase 3 does not yet implement image-to-video. That begins in Phase 7 after the deterministic image pipeline is established.
