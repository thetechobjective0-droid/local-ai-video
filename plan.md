# Local AI Video Generator — Detailed Engineering Plan

## Current implementation checkpoint

**Phases 0–10 repository implementation are complete. Phase 11 web implementation is complete; target-machine acceptance remains pending.** The Phase 11 web layer is a thin local-only interface over existing application services. The API is packaged with FastAPI/Uvicorn and runs on loopback by default. A browser dashboard is served by the same local process. The API/UI must not duplicate generation logic.

The detailed phased plan below is the source of truth and must stay synchronized with meaningful repository commits.

---

# 20. Phase 11 — Local Web API + UI

**Status: IMPLEMENTED — HARDWARE ACCEPTANCE PENDING**

### Delivered

- local FastAPI/Uvicorn server on loopback
- project listing, creation, detail, resume and QA endpoints
- final MP4 access
- unified scene regeneration API for image, audio, or video
- configured local image/TTS/video providers reused by the API
- bounded image/video recovery retained through existing generation services
- browser dashboard with project creation, project list, storyboard scene cards and QA
- scene regeneration stage selector for image/audio/video
- generation busy-state handling in the UI
- scene timing information in storyboard cards
- final video player bound to the project artifact endpoint
- separate UI module to keep API implementation clean
- persisted scene image/audio/video artifact preview endpoints
- scene artifact metadata endpoint with persisted manifest details and safe project-relative file serving
- persisted project timeline JSON endpoint
- persisted SRT/WebVTT subtitle file endpoints
- browser storyboard image, audio and scene-video previews bound to persisted artifact endpoints
- dashboard timeline and narration visibility
- dashboard SRT and WebVTT navigation when subtitle artifacts exist
- API/UI launch and operational documentation in `docs/phase-11-web.md`
- Phase 11 acceptance/status record in `docs/phase-11-status.md`
- README launch instructions and Phase 11 status
- explicit `pathlib.Path` handling for persisted artifact paths in the API
- synchronized `plan.md` after each meaningful implementation increment

### Deferred by design

- persistent background job state and progress reporting
- asynchronous job queues
- frontend build tooling

These remain outside the Phase 11 thin web-layer boundary. Long-running generation is currently synchronous and the dashboard exposes an explicit busy state.

### Acceptance target

```text
Browser -> localhost web UI -> local API -> existing application services
                                      -> project/artifact store
```

The web layer remains local-only, artifact-first, resumable, and provider-agnostic. No cloud inference, upload, telemetry, or duplicated generation logic is permitted.

### Machine acceptance still pending

The repository implementation cannot establish target-hardware behavior. On the Apple M4 / 36 GB machine, execute the documented local workflow and measure model loading, unified-memory pressure, generation latency, thermal behavior, recovery under resource pressure, and subjective visual quality before declaring the system fully production-ready for that hardware.
