# Local AI Video Generator

A local-only AI video production pipeline designed for Apple Silicon, initially targeting an M4 Mac with 36 GB unified memory.

## Current status

**Phase 11 — local web API and browser dashboard implemented; M4 hardware acceptance is pending.**

The project includes the local Director pipeline, scene metadata, deterministic image generation, local macOS TTS, SRT/WebVTT subtitles, deterministic timelines, FFmpeg rendering, bounded media recovery, deterministic motion fallback, a real local AI image-to-video adapter, and a loopback-only FastAPI/Uvicorn dashboard.

## Local-only architecture

All inference and media processing are intended to run on the local machine:

```text
User -> CLI/UI -> Orchestrator -> Ollama/local models -> local media -> FFmpeg -> final.mp4
```

GitHub is used for source control only. The application must not automatically upload prompts, media, artifacts, logs, or telemetry.

## Web dashboard

Install the development environment with `uv` and launch the local dashboard:

```bash
uv sync --extra dev
uv run video-agent-web
```

Open `http://127.0.0.1:8765/` on the same machine. The web server binds to loopback by default and exposes project creation, storyboard inspection, persisted media previews, scene regeneration, QA, timeline/subtitle visibility, and final MP4 playback.

See `docs/phase-11-web.md` for the API surface, artifact safety rules, and operational details.

## Development

Install the base development environment with `uv`:

```bash
uv sync --extra dev
```

For local Diffusers image generation and LTX video generation, install the optional image stack:

```bash
uv sync --extra image
```

Both AI media backends expect **pre-downloaded local model directories**. They use local-only loading and do not download model weights during generation.

### Image generation

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

### AI image-to-video

The first real AI I2V backend is LTX-Video 2B distilled, selected for the 36 GB unified-memory target. The deterministic FFmpeg provider remains the fallback.

```yaml
video:
  provider: ltx_video
  model_path: ./data/models/LTX-Video
  device: mps
  dtype: float16
  width: 704
  height: 384
  fps: 16
```

Generate a scene video after its image exists:

```bash
uv run video-agent generate-video <PROJECT_ID> <SCENE_ID>
```

For deterministic motion without an AI video model:

```yaml
video:
  provider: ffmpeg_ken_burns
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

Run quality checks:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

## Rendering boundary

Phase 6 keeps FFmpeg-specific subprocess construction inside `app/render/ffmpeg.py`. The renderer consumes the persisted `timeline.json`, resolves local artifact metadata, renders the scene sequence, validates the resulting MP4 with `ffprobe`, and persists `final-video.json` plus `render.json`.

Phase 7 scene videos use the same artifact contract, so generated AI clips and deterministic motion clips can feed the renderer without changing rendering business logic.

## Documentation

Read these before contributing:

- `plan.md` — implementation roadmap and architecture
- `AGENTS.md` — AI agent operating contract
- `docs/DOCUMENTATION_STANDARD.md` — documentation Definition of Done
- `docs/phase-7-ltx.md` — local LTX image-to-video backend status
- `docs/phase-11-web.md` — local web API and dashboard guide
- `.agents/skills/` — task-specific engineering playbooks
- `CONTRIBUTING.md` — contribution workflow
- `TESTING.md` — testing strategy

Documentation is a first-class deliverable. Feature changes should update the relevant docs and examples in the same change.

## Repository rule

Do not commit generated video/audio/image assets, model weights, local caches, secrets, or machine-specific state.
