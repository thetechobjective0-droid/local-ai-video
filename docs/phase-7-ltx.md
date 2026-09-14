# Phase 7 — Local AI Image-to-Video Backend

## Model decision

The first real AI image-to-video backend is **LTX-Video 2B distilled**. The project keeps the deterministic FFmpeg motion provider as the fallback.

The selection is based on the target machine rather than maximum model size:

- Apple Silicon M4 with 36 GB unified memory is the primary target.
- LTX-Video documents macOS MPS support.
- The LTX model family provides a 2B distilled checkpoint with substantially lower memory requirements than the 13B variants.
- The 2B distilled checkpoint is suitable for short storyboard-driven clips and is small enough to make local experimentation practical.

The current implementation requires the model to already exist locally. **No model download is performed by the application.**

## Provider

`app/providers/ltx_video.py` implements `LTXVideoProvider` behind the existing `VideoProvider` contract.

The provider:

- loads a local Diffusers-compatible LTX checkpoint with `local_files_only=True`
- uses MPS by default on Apple Silicon
- supports CPU fallback
- uses float16 by default
- converts requested duration/FPS into LTX-compatible frame counts (`8n + 1`)
- accepts the storyboard motion prompt
- writes MP4 output
- records provider/model/device/dtype/frame metadata
- computes an output SHA-256

## Configuration

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

The application never downloads the checkpoint. The model directory must be prepared separately.

## Fallback

```yaml
video:
  provider: ffmpeg_ken_burns
```

This produces deterministic motion from the storyboard image and does not require an AI video model.

## Acceptance still pending

The repository-side adapter is implemented, but actual generation must be validated on the M4 Mac. Measure:

- model load time
- peak unified memory
- generation time per clip
- output dimensions/FPS/duration
- temporal quality
- failure behavior under memory pressure

Do not mark Phase 7 hardware acceptance complete until those measurements are captured.
