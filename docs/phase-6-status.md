# Phase 6 — FFmpeg Rendering

## Status

**Implemented:** deterministic local FFmpeg rendering for contiguous still-image/video timelines with per-scene audio, plus post-render validation.

## Delivered

- Dedicated `FFmpegRenderer` adapter.
- Safe argv-based FFmpeg subprocess invocation; no shell interpolation.
- Resolution/FPS normalization.
- Scene media concatenation through `filter_complex`.
- Per-scene narration audio with silent fallback for scenes without audio.
- H.264 video output with AAC audio.
- `final.mp4` artifact persistence and SHA-256 metadata.
- `render.json` command/filter manifest for reproducibility.
- `ffprobe` post-render validation.
- Validation of video stream, optional/required audio stream, duration, resolution, and FPS.
- Unit coverage for command construction and post-render artifact persistence.

## Rendering boundary

Business logic produces `timeline.json`; FFmpeg command construction is isolated in the renderer adapter. The renderer does not call cloud services and does not upload media.

The initial renderer requires contiguous scene timing. Gap/fade transitions and advanced motion effects remain later-stage work.

## CLI integration

The rendering adapter is ready to be exposed through the project CLI as the next integration step.

## Acceptance target

A 30–60 second project composed of local still images plus narration should render to an H.264/AAC MP4 and pass `ffprobe` validation.
