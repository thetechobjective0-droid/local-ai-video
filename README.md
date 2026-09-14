# Local AI Video Generator

A local-only AI video production pipeline designed for Apple Silicon, initially targeting an M4 Mac with 36 GB unified memory.

## Current status

**Phase 3 — Local image generation implemented; M4 model acceptance pending.**

The project now includes the local Director pipeline, richer scene metadata, deterministic timing validation, a provider-agnostic image-generation contract, and a local Diffusers text-to-image backend designed for Apple Silicon MPS.

## Local-only architecture

All inference and media processing are intended to run on the local machine:

```text
User -> CLI/UI -> Orchestrator -> Ollama/local models -> local media -> FFmpeg -> final.mp4
```

GitHub is used for source control only. The application must not automatically upload prompts, media, artifacts, logs, or telemetry.

## Development

Install the base development environment with `uv`:

```bash
uv sync --extra dev
```

For local Diffusers image generation, install the optional image stack:

```bash
uv sync --extra image
```

The image backend expects a **pre-downloaded local Diffusers model directory**. It uses `local_files_only=True`; it does not download model weights during generation.

Configure the local model in YAML when needed:

```yaml
image:
  provider: diffusers
  model_path: ./data/models/stable-diffusion-xl-base-1.0
  device: mps
  width: 1024
  height: 576
  steps: 30
  guidance_scale: 7.0
```

Run the CLI:

```bash
uv run video-agent health
uv run video-agent doctor
```

Run tests:

```bash
uv run pytest
```

Run quality checks:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

## Image generation API

The application boundary is provider-agnostic:

```python
class ImageProvider(Protocol):
    def generate(self, request: ImageGenerationRequest) -> ImageResult: ...
```

A scene can be generated independently through the deterministic image service. The service persists the PNG, artifact metadata, generation parameters, SHA-256 output hash, and updated scene reference.

## Documentation

Read these before contributing:

- `plan.md` — implementation roadmap and architecture
- `AGENTS.md` — AI agent operating contract
- `docs/DOCUMENTATION_STANDARD.md` — documentation Definition of Done
- `.agents/skills/` — task-specific engineering playbooks
- `CONTRIBUTING.md` — contribution workflow
- `TESTING.md` — testing strategy

Documentation is a first-class deliverable. Feature changes should update the relevant docs and examples in the same change.

## Repository rule

Do not commit generated video/audio/image assets, model weights, local caches, secrets, or machine-specific state.
