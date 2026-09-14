# Local AI Video Generator — Detailed Engineering Plan

## Current implementation checkpoint

**Phases 0–10 repository implementation are complete. Phase 11 web implementation is complete. Phase 12 local job orchestration is implemented; target-machine acceptance remains pending.** The web layer remains a thin local-only interface over existing application services. Long-running media generation now runs in a persistent, JSON-backed local worker with browser status polling. No cloud queue or external service is used.

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
- scene timing, timeline and narration visibility
- persisted scene image/audio/video artifact previews and metadata
- persisted project timeline JSON endpoint
- persisted SRT/WebVTT subtitle endpoints
- final video player
- explicit safe project-relative artifact path handling
- API/UI launch and operational documentation

### Deferred by design

- background job state and asynchronous execution (delivered in Phase 12)
- frontend build tooling

---

# 21. Phase 12 — Local Job Orchestration

**Status: IMPLEMENTED — HARDWARE ACCEPTANCE PENDING**

### Delivered

- persistent local JSON job manifests under the configured storage root
- job lifecycle states: `queued → running → completed/failed`
- `interrupted` state for jobs found active after process restart
- single-worker local `ThreadPoolExecutor` to bound resource contention
- worker delegates to existing `generate_project_media`; no generation logic is duplicated
- atomic job persistence and durable timestamps/errors
- per-scene progress persistence (`completed_scenes` / `scene_count`)
- API submission/status/list endpoints:
  - `POST /api/projects/{project_id}/jobs/media`
  - `GET /api/jobs/{job_id}`
  - `GET /api/projects/{project_id}/jobs`
- HTTP 202 submission semantics
- browser background-generation control
- 2-second job polling and automatic artifact refresh on terminal state
- stale queued/running jobs are marked `interrupted` on process restart
- Phase 12 operational documentation in `docs/phase-12-jobs.md`
- plan synchronized with Phase 12 implementation
- `run.sh` main-branch launcher that updates `main`, syncs dependencies, validates local prerequisites, checks Ollama, and starts the web dashboard

### Design constraints

The worker is intentionally process-local. There is no Redis, Celery, cloud queue, remote inference, telemetry, or upload path. One worker is the default to prevent uncontrolled unified-memory pressure on the target Apple M4 / 36 GB machine.

### Acceptance target

```text
Browser -> localhost API -> persistent local job manifest
                         -> local worker -> existing media orchestrator
                         -> project/artifact store
```

The job layer owns scheduling and lifecycle state only. The existing media orchestration layer remains responsible for provider routing, recovery, caching, artifact persistence and project status.

### Machine acceptance still pending

On the Apple M4 / 36 GB machine, execute the documented local workflow and measure model loading, unified-memory pressure, generation latency, thermal behavior, restart recovery and subjective visual quality before declaring the system fully production-ready for that hardware.
