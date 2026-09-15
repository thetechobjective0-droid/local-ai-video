# Local AI Video Generator

A local-only AI video production pipeline designed for Apple Silicon, initially targeting an M4 Mac with 36 GB unified memory.

## Current video architecture

The production default generates **real temporal AI video**, not a slideshow or Ken-Burns animation:

```text
User prompt
  -> local Ollama Director
  -> storyboard + scene keyframes
  -> LTX-2.3 MLX image-to-video
  -> real temporal frames + synchronized native audio
  -> timeline/subtitles
  -> FFmpeg final MP4
```

The default Apple-Silicon provider is `ltx2_mlx`. The older PyTorch `ltx_video` adapter remains available, and `ffmpeg_ken_burns` is an explicit deterministic fallback only.

## One-command local setup

On the target Apple-Silicon Mac, use:

```bash
./run.sh
```

`run.sh` checks the local macOS/arm64 prerequisites, syncs this application's Python environment, clones and syncs the LTX-2.3 MLX runtime into `data/runtime/ltx-2-mlx` when it is missing, validates the local runtime/model directories, checks Ollama, and starts the browser dashboard.

The script never downloads model weights for you. Prepare the local LTX-2.3 q8 model pack at `data/models/ltx-2.3-mlx-q8` according to `docs/ltx2-mlx.md` before the first generation run.

Environment overrides are supported for the runtime/model locations:

```bash
LTX_RUNTIME_DIR=/custom/ltx-2-mlx \
LTX_RUNTIME_REPO=https://github.com/appautomaton/ltx-video-mlx.git \
LTX_MODEL_DIR=/custom/ltx-2.3-mlx-q8 \
./run.sh
```

## Local-only runtime

All inference and media processing run locally. No prompts, media, artifacts, logs, or telemetry are uploaded by the application.

The LTX-2.3 MLX runtime is an external local dependency because it uses a separate Apple-Silicon MLX environment. The application invokes it with `uv run --offline`, so generation cannot silently install or download dependencies.

### Manual runtime setup

When `run.sh` is not used:

```bash
mkdir -p data/runtime
git clone https://github.com/appautomaton/ltx-video-mlx.git data/runtime/ltx-2-mlx
cd data/runtime/ltx-2-mlx
uv sync
cd ../..
```

Prepare the local LTX-2.3 weights inside that runtime following `docs/ltx2-mlx.md`.

### Configuration

```yaml
video:
  provider: ltx2_mlx
  engine_path: ./data/runtime/ltx-2-mlx
  model_path: ./data/models/ltx-2.3-mlx-q8
  uv_command: uv
  low_ram: true
  pipeline: two-stage
  bits: 8
  native_audio: true
  i2v_strength: 0.95
  allow_fallback: false
  width: 704
  height: 480
  fps: 24
```

Real AI scenes are intentionally constrained to 5–10 seconds so the storyboard produces model-sized temporal clips. Longer videos are assembled from multiple generated scenes.

## Web dashboard

```bash
uv sync --extra dev
uv run video-agent-web
```

Open `http://127.0.0.1:8765/` on the same machine. The UI is the primary workflow for project creation, storyboard inspection, media generation, scene regeneration, QA, and final MP4 playback.

The scene cards identify whether a clip is:

- `AI temporal video` — real temporal generation from an AI I2V backend.
- `Deterministic image motion` — explicit FFmpeg still-image animation.

## Image generation

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

## Explicit deterministic fallback

Use this only when you intentionally want still-image motion instead of AI video:

```yaml
video:
  provider: ffmpeg_ken_burns
```

The application never silently switches from an AI provider to this fallback unless `allow_fallback: true` is explicitly configured.

## Development

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

## Documentation

- `plan.md` — implementation roadmap and architecture
- `docs/ltx2-mlx.md` — real Apple-Silicon LTX-2.3 runtime setup
- `docs/phase-7-ltx.md` — legacy PyTorch LTX-Video backend
- `docs/phase-11-web.md` — local web API and dashboard guide
- `.agents/skills/` — task-specific engineering playbooks
- `CONTRIBUTING.md` — contribution workflow
- `TESTING.md` — CI/test strategy

Do not commit generated media, model weights, local caches, secrets, or machine-specific state.
