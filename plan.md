# Local AI Video Generator — Detailed Engineering Plan

## Current implementation checkpoint

**Phases 0–10 repository implementation are complete. Phase 11 is now in progress.** The Phase 11 web layer is a thin local-only interface over existing application services. The API is packaged with FastAPI/Uvicorn and runs on loopback by default. A browser dashboard is now served by the same local process. The API/UI must not duplicate generation logic. Target Apple M4 / 36 GB hardware acceptance remains a machine-level activity for actual model loading, memory pressure, generation latency, thermal behavior, and subjective visual quality.

The detailed phased plan below is the source of truth and must stay synchronized with meaningful repository commits.

---

# 20. Phase 11 — Local Web API + UI

**Status: IN PROGRESS — ARTIFACT PREVIEWS**

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
- synchronized `plan.md` after each meaningful implementation increment
- persisted scene image/audio/video artifact preview endpoints
- scene artifact metadata endpoint with persisted manifest details and safe project-relative file serving
- persisted project timeline JSON endpoint
- persisted SRT/WebVTT subtitle file endpoints

### Remaining

- bind the new artifact endpoints into the browser storyboard UI
- improve long-running generation status visibility
- add API/UI documentation and launch instructions
- add Phase 11 acceptance/status documentation

### Acceptance target

```text
Browser -> localhost web UI -> local API -> existing application services
                                      -> project/artifact store
```

The web layer must remain local-only, artifact-first, resumable, and provider-agnostic. No cloud inference, upload, telemetry, or duplicated generation logic is permitted.
