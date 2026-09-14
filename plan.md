# Local AI Video Generator — Detailed Engineering Plan

## Current implementation checkpoint

**Phases 0–10 repository implementation are complete. Phase 11 web implementation is complete. Phase 12 local job orchestration is implemented; target-machine acceptance remains pending.** The web layer remains a thin local-only interface over existing application services. Long-running media generation now runs in persistent, JSON-backed local workers with browser status polling. Project planning is also asynchronous so HTTP project creation is not blocked by the three-stage Ollama Director pipeline. No cloud queue or external service is used.

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
- asynchronous project creation: filesystem metadata is returned immediately while Ollama planning runs in a local background worker
- validated asynchronous project creation request schema with forbidden unknown fields
- planning job status endpoint
- dashboard planning status and 2-second polling, with automatic project refresh after planning completes or fails
- QA endpoint serializes the dataclass report correctly for FastAPI JSON responses
- API/UI launch and operational documentation
- launcher displays the actual loopback port used by Uvicorn (`8765`)

### Deferred by design

- background media job state and asynchronous execution (delivered in Phase 12)
- frontend build tooling

---

# 21. Phase 12 — Local Job Orchestration

**Status: IMPLEMENTED — HARDWARE ACCEPTANCE PENDING**

### Delivered

- persistent local JSON job manifests under the configured storage root
- media job lifecycle states: `queued → running → completed/failed`
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
- persistent local planning job manifests under `planning-jobs`
- planning worker uses one local worker to avoid competing for unified memory with media generation
- planning request validation is centralized in `app/job_api.py`; the unused duplicate planning router module was removed
- Ruff CI now enforces correctness-oriented `E`, `F`, and `B` rules; formatter handles layout and long embedded strings are exempted from E501, while Typer option/argument declarations are treated as intentional immutable calls
- subtitle cue generation now uses explicit `zip(..., strict=True)` semantics
- strict mypy configuration keeps heavy optional ML packages out of the CI environment while preserving type checking of application boundaries
- corrected Python health-check field typing for strict mypy
- typed the optional LTX video provider boundary
- Phase 12 operational documentation in `docs/phase-12-jobs.md`
- plan synchronized with Phase 12 implementation
- `run.sh` launcher uses the existing local checkout, syncs dependencies, validates local prerequisites, checks Ollama, and starts the web dashboard

### Design constraints

The workers are intentionally process-local. There is no Redis, Celery, cloud queue, remote inference, telemetry, or upload path. One worker per job manager is the default to prevent uncontrolled unified-memory pressure on the target Apple M4 / 36 GB machine.

### Acceptance target

```text
Browser -> localhost API -> persistent local project/job manifests
                         -> local planning worker -> Ollama -> Director artifacts
                         -> local media worker -> existing media orchestrator
                         -> project/artifact store
```

The job layers own scheduling and lifecycle state only. The existing Director and media orchestration layers remain responsible for validation, provider routing, recovery, caching, artifact persistence and project status.

### Machine acceptance still pending

On the Apple M4 / 36 GB machine, execute the documented local workflow and measure model loading, unified-memory pressure, generation latency, thermal behavior, restart recovery and subjective visual quality before declaring the system fully production-ready for that hardware.
