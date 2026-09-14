# Phase 9 — Quality Assurance

## Status

**IN PROGRESS**

Phase 9 starts with deterministic media-integrity and project-consistency QA. The goal is to reject corrupt or inconsistent artifacts before rendering and identify the exact scene/artifact that requires regeneration.

## Implemented

- `validate_image()` checks PNG integrity, dimensions, and SHA-256.
- `validate_audio()` checks FFprobe decoding, audio-stream presence, and duration.
- Existing video validation checks decoding, stream presence, duration, resolution, and FPS.
- `validate_project()` aggregates scene, asset, timeline, subtitle, and final-video failures into actionable scoped failures.
- Scene asset UUIDs are checked against their persisted artifact manifests.
- Timeline project identity, duration, contiguity, scene coverage, and positive durations are checked.
- Subtitle-file existence is checked against the timeline's configured format.
- Final-video QA reuses the deterministic Phase 6 validator when `final.mp4` exists.

## QA boundary

```text
Generated artifact
       |
       v
Integrity / metadata QA
       |
       +---- FAIL --> identify exact scene/artifact --> targeted regeneration
       |
       +---- PASS --> persist / continue pipeline
```

QA does not silently repair corrupted media and does not use an LLM to decide whether an artifact is valid.

## Current limitations

- Image QA validates PNG structure and dimensions but does not yet perform perceptual blank-image detection.
- Audio QA validates decoding and duration but does not yet perform loudness or silence analysis.
- Video QA is deterministic metadata/decode validation; semantic visual-quality scoring is not implemented.
- Project QA is currently an application API; CLI exposure and automatic render-stage integration are next.

## Next

1. Expose project QA through the CLI.
2. Add targeted regeneration commands based on scoped QA failures.
3. Add deterministic audio loudness/silence checks.
4. Add practical image blank/invalid-content detection.
5. Integrate project QA into the final render gate.
6. Add Phase 9 acceptance coverage and M4 end-to-end validation.
