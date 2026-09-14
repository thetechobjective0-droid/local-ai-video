# Phase 5 — Subtitles and Timeline

## Status

**Implemented:** deterministic timeline manifest plus SRT/WebVTT subtitle generation.

## Delivered

- Typed `Timeline` and `TimelineScene` Pydantic models.
- Deterministic scene ordering by scene index.
- Timeline validation for overlapping scenes and project-duration overflow.
- Persisted `timeline.json` project artifact.
- Deterministic scene-level subtitle generation.
- Stable proportional cue timing when word-level timestamps are unavailable.
- Configurable subtitle line width.
- SRT output.
- WebVTT output.
- CLI commands:

```bash
video-agent timeline <PROJECT_ID>
video-agent subtitles <PROJECT_ID> --max-chars 48
```

- Unit coverage for subtitle formatting, empty narration, timeline ordering, media references, and overlap rejection.

## Design boundary

The timeline is a deterministic intermediate representation. Rendering code should consume this manifest rather than embed one-off FFmpeg command construction throughout business logic.

Subtitle timing is scene-derived in this phase. Provider-specific word timestamps can be introduced later without changing the SRT/WebVTT boundary.

## Next

Phase 6 will consume the timeline and local media artifacts to produce and validate the final MP4 through a dedicated FFmpeg rendering adapter.
