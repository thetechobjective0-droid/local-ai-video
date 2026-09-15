# Local Video Quality Guide

## Why the deterministic fallback looks weaker

`ffmpeg_ken_burns` animates a still image with deterministic pan/zoom. It is intentionally reliable, but it does not synthesize new temporal content. For materially better motion, configure the local `ltx_video` provider with a downloaded LTX-Video checkpoint.

## Recommended quality configuration

Use the project `config.example.yaml` as the starting point:

```yaml
runtime:
  profile: quality

video:
  provider: ltx_video
  model_path: ./data/models/LTX-Video
  device: mps
  dtype: float16
  width: 704
  height: 480
  fps: 24
  inference_steps: 40
  guidance_scale: 3.0
  guidance_rescale: 0.0
  image_cond_noise_scale: 0.025
  decode_timestep: 0.05
  decode_noise_scale: 0.025
```

The generation path now passes the full visual/camera/composition/lighting context into the I2V prompt, applies a temporal-quality negative prompt when none is supplied, and records all effective quality parameters in the artifact manifest for reproducibility.

## Quality ladder

- `ffmpeg_ken_burns`: fastest and most reliable; still-image animation only.
- `ltx_video` balanced settings: local AI motion with moderate compute cost.
- `ltx_video` quality settings: more denoising steps and higher temporal fidelity at higher memory/time cost.

Current LTX Diffusers guidance documents image-to-video generation with explicit negative prompts, denoising steps, guidance, image-conditioning noise, and timestep-aware decode controls. Target-machine tuning remains necessary because M4 memory pressure varies with checkpoint size and resolution.
