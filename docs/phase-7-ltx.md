# Phase 7 — Local AI Image-to-Video Backend

## Model decision

The first real AI image-to-video backend is **LTX-Video 2B distilled**. The deterministic FFmpeg motion provider remains an explicit operator-selected fallback, not an automatic substitute for failed AI generation.

The selection is based on the target machine rather than maximum model size:

- Apple Silicon M4 with 36 GB unified memory is the primary target.
- LTX-Video documents macOS MPS support.
- The LTX model family provides smaller checkpoints suitable for local experimentation.
- The provider is designed for short storyboard-driven temporal clips on the target machine.

The current implementation requires the model to already exist locally. **No model download is performed by the application.**

## Provider

`app/providers/ltx_video.py` implements `LTXVideoProvider` behind the existing `VideoProvider` contract.

The provider:

- loads a local Diffusers-compatible LTX checkpoint with `local_files_only=True`
- uses the dedicated `LTXImageToVideoPipeline`
- uses MPS by default on Apple Silicon
- supports CPU fallback
- uses float16 by default
- converts requested duration/FPS into LTX-compatible frame counts (`8n + 1`)
- conditions generation on the scene image and motion/shot context
- records explicit `generation_mode=ai_i2v` and `temporal_generation=true`
- writes MP4 output
- records provider/model/device/dtype/frame metadata
- computes an output SHA-256

## Routing invariant

When `ltx_video` is configured, scene routing prioritizes `IMAGE_TO_VIDEO` even if the storyboard's media preference is static image. The LTX capability is strict: unsupported duration or memory conditions fail the scene instead of falling through to static/FFmpeg media.

## Configuration

```yaml
video:
  provider: ltx_video
  model_path: ./data/models/LTX-Video
  allow_fallback: false
  device: mps
  dtype: float16
  width: 704
  height: 480
  fps: 24
```

The application never downloads the checkpoint. The model directory must be prepared separately.

## Deterministic motion mode

```yaml
video:
  provider: ffmpeg_ken_burns
```

This produces deterministic motion from the storyboard image and does not require an AI video model. The dashboard labels these clips as `Deterministic image motion (FFmpeg)` so they cannot be confused with AI temporal generation.

## Acceptance

Actual generation must still be validated on the M4 Mac. Measure:

- model load time
- peak unified memory
- generation time per clip
- output dimensions/FPS/duration
- temporal quality
- failure behavior under memory pressure
- visual comparison against the previous still-image baseline

Do not mark Phase 7 hardware acceptance complete until those measurements are captured.
