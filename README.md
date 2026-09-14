# Local AI Video Generator

A local-only AI video production pipeline designed for Apple Silicon, initially targeting an M4 Mac with 36 GB unified memory.

## Current status

**Phase 6 — FFmpeg rendering implemented; final MP4 rendering and post-render validation are now wired through the CLI.**

The project includes the local Director pipeline, scene metadata, deterministic image generation, local macOS TTS, SRT/WebVTT subtitles, deterministic timelines, and an isolated FFmpeg renderer for producing H.264/AAC MP4 output.

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

Generate a deterministic timeline and render it:

```bash
uv run video-agent timeline <PROJECT_ID>
uv run video-agent render <PROJECT_ID>
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

## Rendering boundary

Phase 6 keeps FFmpeg-specific subprocess construction inside `app/render/ffmpeg.py`. The renderer consumes the persisted `timeline.json`, resolves local artifact metadata, renders the scene sequence, validates the resulting MP4 with `ffprobe`, and persists `final-video.json` plus `render.json`.

The initial renderer requires contiguous scene timing and supports local still-image/video media plus per-scene narration. More advanced transitions and AI-generated video clips are later phases.

## Documentation

Read these before contributing:

- `plan.md` — implementation roadmap and architecture
- `AGENTS.md` — AI agent operating contract
- `docs/DOCUMENTATION_STANDARD.md` — documentation Definition of Done
- `docs/phase-6-status.md` — current FFmpeg implementation status
- `.agents/skills/` — task-specific engineering playbooks
- `CONTRIBUTING.md` — contribution workflow
- `TESTING.md` — testing strategy

Documentation is a first-class deliverable. Feature changes should update the relevant docs and examples in the same change.

## Repository rule

Do not commit generated video/audio/image assets, model weights, local caches, secrets, or machine-specific state.
