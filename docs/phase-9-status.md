# Phase 9 — Quality Assurance

## Status

**COMPLETE — DETERMINISTIC QA**

Phase 9 provides deterministic media/project validation, machine-readable QA reporting, targeted scene regeneration, audio quality gates, timeline/subtitle validation, and final-video validation.

## Implemented

### Media integrity

- Image: existence, PNG signature/IHDR, positive dimensions, optional dimensions, SHA-256.
- Audio: existence, FFprobe decode/stream validation, positive duration, expected-duration tolerance.
- Video: existence, FFprobe metadata, video stream, duration, resolution/FPS, complete FFmpeg decode.

### Audio quality

- FFmpeg `volumedetect` peak measurement.
- Clipping/headroom gate with configurable maximum peak.
- FFmpeg `silencedetect` analysis.
- Entirely-silent narration rejection.
- Measured peak, duration, silence-event count, and silent-duration reporting.

### Project QA

- project/scene/artifact manifest validation
- scene/artifact UUID consistency
- per-scene image/audio/video validation
- timeline project/duration/continuity validation
- scene coverage validation
- subtitle file presence validation
- final MP4 validation
- final audio quality validation when final output exists

### QA reporting and targeted regeneration

```bash
uv run video-agent qa <PROJECT_ID>
uv run video-agent regenerate-scene <PROJECT_ID> <SCENE_ID> --stage image
uv run video-agent regenerate-scene <PROJECT_ID> <SCENE_ID> --stage audio
uv run video-agent regenerate-scene <PROJECT_ID> <SCENE_ID> --stage video
uv run video-agent regenerate-scene <PROJECT_ID> <SCENE_ID> --stage all
```

`qa-report.json` contains a schema version, pass/fail state, and exact failure scope/message. Targeted regeneration invalidates affected downstream artifacts/cache state and reruns project QA.

## Acceptance boundary

Phase 9 deterministic code paths are complete. CI is responsible for repository validation. Actual model inference, media generation performance, memory pressure, and visual-quality acceptance still require the target Apple M4 / 36 GB machine with locally stored model weights and installed media runtimes.

Visual-semantic quality scoring is intentionally deferred to the evaluation/recovery phases; deterministic QA does not pretend to measure subjective visual quality.

## Next phase

**Phase 10 — Agentic Recovery and Refinement.**
