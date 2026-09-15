# LTX-2.3 MLX Runtime

The production Apple-Silicon video path uses the local `dgrauet/ltx-2-mlx` runtime. It is a pure MLX port of LTX-2.3 with text-to-video, image-to-video, synchronized audio, two-stage generation, and low-memory block streaming. The published runtime targets Apple Silicon and the q8 model is intended for local MLX inference. citeturn811721search1turn811721search2

The application invokes the runtime with `uv run --offline`, so generation itself never downloads packages or model weights. `run.sh` can prepare the runtime and, with confirmation, download the model pack into the configured local directory.

## One-command setup

From the repository root:

```bash
chmod +x run.sh
./run.sh
```

When the q8 model is missing, `run.sh` asks whether it should download `dgrauet/ltx-2.3-mlx-q8` into:

```text
data/models/ltx-2.3-mlx-q8
```

The current q8 repository is large (about 72 GB according to Hugging Face), so the download is intentionally interactive by default. citeturn811721search2

To make the behavior non-interactive:

```bash
LTX_AUTO_DOWNLOAD_MODEL=yes ./run.sh
```

To force the old fail-fast/manual-preparation behavior:

```bash
LTX_AUTO_DOWNLOAD_MODEL=no ./run.sh
```

The model source can also be overridden for a compatible local model pack:

```bash
LTX_MODEL_REPO=dgrauet/ltx-2.3-mlx-q8 \
LTX_MODEL_DIR=./data/models/ltx-2.3-mlx-q8 \
./run.sh
```

## Prepare the runtime manually

```bash
mkdir -p data/runtime
git clone https://github.com/dgrauet/ltx-2-mlx.git data/runtime/ltx-2-mlx
cd data/runtime/ltx-2-mlx
uv sync --all-extras
```

Prepare the q8 model pack with Hugging Face:

```bash
uv tool run --from "huggingface_hub[hf_xet]" huggingface-cli download \
  dgrauet/ltx-2.3-mlx-q8 \
  --local-dir "$PWD/../../data/models/ltx-2.3-mlx-q8"
```

The model repository documents the same local-download flow and includes the required MLX safetensors, audio VAE, VAE, vocoder, and configuration files. citeturn811721search2

## Application configuration

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
  allow_fallback: false
  width: 704
  height: 480
  fps: 24
```

The MLX runtime exposes `generate` for T2V/I2V generation and supports `--two-stage`, `--two-stages-hq`, `--low-ram`, and q8 model weights. citeturn811721search1

## Generation contract

Each storyboard scene is constrained to 5–10 seconds. The scene image becomes the I2V conditioning image and `motion_prompt` describes concrete temporal actions. The MLX provider returns a real multi-frame MP4 and, when audio is generated, the application extracts its synchronized audio track into the scene audio artifact.

The output is tagged with:

```text
generation_mode=ai_i2v
temporal_generation=true
```

A failed model invocation is a hard failure by default. The system cannot silently turn an AI-video request into a Ken-Burns clip.

## Performance and memory

For the 36 GB M4 target, start with q8 + `two-stage` + `low_ram: true` at 704x480 / 24 FPS. The runtime documents block-streaming and additional tiling options for workloads that exceed available unified memory. citeturn811721search1

The target-machine acceptance step must still measure actual generation latency, peak unified memory, thermals, and temporal/audio quality on the user's M4 because those values cannot be established from repository code alone.
