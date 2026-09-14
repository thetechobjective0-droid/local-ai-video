# Phase 11 Acceptance Status

**Status: IMPLEMENTED — HARDWARE ACCEPTANCE PENDING**

## Scope completed

Phase 11 provides a loopback-only FastAPI/Uvicorn service and a browser dashboard over the existing local-first pipeline.

### API

- health check
- project listing and creation
- project detail and Director resume
- project QA
- timeline retrieval
- SRT/WebVTT subtitle serving
- scene image/audio/video artifact serving
- scene artifact manifest retrieval
- scene image/audio/video regeneration
- final MP4 serving

### UI

- project creation form
- project browser
- project status and metadata
- storyboard scene cards
- scene timing and narration
- image, audio, and video previews from persisted artifacts
- scene-level regeneration controls
- QA result display
- timeline and subtitle navigation
- final MP4 playback

## Architecture acceptance

```text
Browser
  |
  v
127.0.0.1:8765
  |
  +--> FastAPI routes
  |
  +--> existing Director / generation / QA services
  |
  +--> configured project artifact store
```

The web layer does not introduce a second generation implementation. Generation remains delegated to the existing application services and provider contracts.

## Security and locality

- Server binds to loopback (`127.0.0.1`).
- Generation routes require `runtime.local_only`.
- Artifact file paths are resolved and constrained beneath the project directory.
- Browser requests cannot supply arbitrary filesystem paths.
- No cloud inference, automatic upload, or telemetry path was added.

## Deferred work

Persistent background-job status and progress reporting are not part of this acceptance. Generation requests are synchronous; the UI exposes a busy state while a request is active. A later phase can introduce a persistent job model without moving orchestration logic into the web layer.

## Hardware acceptance

Repository implementation is complete, but the actual M4 / 36 GB acceptance still requires execution on the target machine with the configured local models. The remaining machine-level checks are model loading, unified-memory pressure, generation latency, thermal behavior, recovery behavior under resource pressure, and subjective output quality.
