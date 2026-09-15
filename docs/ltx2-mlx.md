# LTX-2.3 MLX Runtime

The production Apple-Silicon video path uses the local `dgrauet/ltx-2-mlx` runtime. It is a pure MLX port of LTX-2.3 with text-to-video, image-to-video, synchronized audio, two-stage generation, and low-memory block streaming. The published runtime targets Apple Silicon M1/M2/M3/M4 and recommends 32 GB+ RAM for the q8 model; this project targets an M4 with 36 GB unified memory. citeturn653340search0

The application invokes the runtime with `uv run --offline`, so generation never downloads packages or model weights. All model assets must be prepared locally first.

## Prepare the runtime

```bash
mkdir -p data/runtime
git clone https://github.com/dgrauet/ltx-2-mlx.git data/runtime/ltx-2-mlx
cd data/runtime/ltx-2-mlx
uv sync --all-extras
```

Prepare a local LTX-2.3 q8 model pack at:

```text
data/models/ltx-2.3-mlx-q8
```

The MLX runtime also supports q4 and bf16 variants, but q8 is the default for the 36 GB M4 target. The runtime documents q8 as the recommended memory/quality compromise and supports `--low-ram` block streaming when additional memory protection is needed. citeturn660719search0

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

The two-stage pipeline is the production default because the MLX runtime documents it as the recommended mode for most use cases. citeturn653340search0

## Generation contract

Each storyboard scene is constrained to 5–10 seconds. The scene image becomes the I2V conditioning image and `motion_prompt` describes concrete temporal actions. The MLX provider returns a real multi-frame MP4 and, when audio is generated, the application extracts its synchronized audio track into the scene audio artifact.

The output is tagged with:

```text
generation_mode=ai_i2v
temporal_generation=true
```

A failed model invocation is a hard failure by default. The system cannot silently turn an AI-video request into a Ken-Burns clip.

## Performance and memory

For a 36 GB M4, start with q8 + `two-stage` + `low_ram: true` at 704x480 / 24 FPS. The external MLX runtime provides additional `--tile-frames`, `--tile-spatial`, and lower-bit model options for larger workloads. citeturn660719search0

The target-machine acceptance step must still measure actual generation latency, peak unified memory, thermals, and temporal quality on the user's M4 because those values cannot be established from repository code alone.
