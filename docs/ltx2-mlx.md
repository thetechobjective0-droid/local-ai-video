# LTX-2.3 MLX Runtime

The production Apple-Silicon video path uses the local `ltx-video-mlx` runtime. It provides real temporal text-to-video/image-to-video generation and synchronized audio without requiring PyTorch in the runtime process.

The application invokes the runtime through `uv run --offline`, so it never downloads model weights or Python packages during generation. The runtime must be prepared locally before the dashboard is used.

## Prepare the runtime

```bash
mkdir -p data/runtime
git clone https://github.com/appautomaton/ltx-video-mlx.git data/runtime/ltx-video-mlx
cd data/runtime/ltx-video-mlx
uv sync
```

Prepare the model weights inside that runtime according to its local model instructions. The current Apple-Silicon path uses the LTX-2.3 FP8 weights with the distilled runtime. The published MLX project documents 8-bit and 4-bit inference and an Apple-Silicon memory footprint suitable for local experimentation. citeturn639771view0

The application expects:

```text
data/runtime/ltx-video-mlx/generate.py
data/runtime/ltx-video-mlx/models/...
```

## Application configuration

```yaml
video:
  provider: ltx2_mlx
  engine_path: ./data/runtime/ltx-video-mlx
  uv_command: uv
  bits: 8
  native_audio: true
  i2v_strength: 0.95
  allow_fallback: false
  width: 768
  height: 512
  fps: 25
```

`allow_fallback` is intentionally false by default. A failed LTX-2 run must not silently become a Ken-Burns slideshow.

## Generation contract

Each storyboard scene is kept at 5–10 seconds for the MLX video path. The scene image is passed to LTX-2.3 as the conditioning image, and the motion prompt is passed as the temporal action description. The provider returns:

- a real multi-frame MP4;
- a native synchronized WAV track when audio generation is enabled;
- provenance metadata identifying `generation_mode=ai_i2v` and `temporal_generation=true`.

The orchestrator persists the generated WAV as the scene audio artifact so the canonical final renderer keeps the synchronized generated audio instead of replacing it with macOS TTS.

## Prompting a performance

Prompts should describe concrete actions, not merely the still image. For example:

```text
An anthropomorphic orange cat drives a small red convertible down a sunny coastal road. The cat grips the steering wheel, turns its head toward the passenger seat, bobs to the rhythm while singing happily, the car moves steadily forward, road markings and trees pass with natural parallax, gentle handheld tracking camera.
```

LTX-2.3 jointly models audio and video, so action/performance wording such as `singing happily`, `speaking`, environmental sound, or music cues can be part of the generation prompt. The official Diffusers LTX-2 documentation describes the model as a synchronized audio-video generator. citeturn110953search0turn110953search2

## Operational note

The model and runtime remain external local assets. They are not committed to Git. For a fresh machine, run the environment checks before creating a project and verify that `data/runtime/ltx-video-mlx/generate.py` exists.
