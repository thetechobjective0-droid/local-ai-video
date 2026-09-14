# Local AI Video Generator — Detailed Engineering Plan

## Current implementation checkpoint

**Phases 0–10 repository implementation are complete. Phase 11 is now in progress.** The Phase 11 web layer is a thin local-only interface over existing application services. The API is packaged with FastAPI/Uvicorn and runs on loopback by default. A browser dashboard is now served by the same local process. The API/UI must not duplicate generation logic. Target Apple M4 / 36 GB hardware acceptance remains a machine-level activity for actual model loading, memory pressure, generation latency, thermal behavior, and subjective visual quality.

The detailed phased plan below is the source of truth and must stay synchronized with meaningful repository commits.

---

# 20. Phase 11 — Local Web API + UI

**Status: IN PROGRESS — API + UI FOUNDATION**

### Delivered

- created `phase11-web-api` branch from the Phase 10 implementation line
- added localhost-oriented FastAPI application entry point
- added project listing and project-detail endpoints
- added project creation and Director resume endpoints
- added deterministic project QA endpoint with persisted `qa-report.json`
- added final MP4 artifact endpoint
- added scene video regeneration endpoint using existing bounded recovery
- added FastAPI and Uvicorn runtime dependencies
- added `video-agent-web` launch entry point
- enforced loopback binding (`127.0.0.1`) for the web server
- hardened request validation and local-only configuration checks
- added a browser dashboard served at `/`
- added project creation form and project list
- added project detail/storyboard scene cards
- added QA result display
- added targeted scene video regeneration control
- added final video opening control
- kept UI markup separate from API implementation to avoid circular dependencies
- kept API orchestration thin and delegated to existing application services

### Remaining

- improve generation controls/status visibility for long-running workflows
- expose image/audio regeneration controls through the UI
- add richer artifact previews and timeline information
- add API/UI documentation and launch instructions
- add Phase 11 acceptance/status documentation

### Acceptance target

```text
Browser -> localhost web UI -> local API -> existing application services
                                      -> project/artifact store
```

The web layer must remain local-only, artifact-first, resumable, and provider-agnostic. No cloud inference, upload, telemetry, or duplicated generation logic is permitted.
