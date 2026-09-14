# Local AI Video Generator — Detailed Engineering Plan

## Current implementation checkpoint

**Phases 0–10 repository implementation are complete. Phase 11 web implementation is complete. Phase 12 local job orchestration is implemented; target-machine acceptance remains pending.** The web layer remains a thin local-only interface over existing application services. Long-running media generation now runs in persistent, JSON-backed local workers with browser status polling. Project planning is also asynchronous so HTTP project creation is not blocked by the three-stage Ollama Director pipeline. Media submission is explicitly gated on planning completion so the dashboard cannot race the storyboard worker. Planning jobs also perform one bounded retry from persisted artifacts when the first model attempt fails. The dashboard now distinguishes planning state from media-job state and only presents the final video player when a final MP4 actually exists.

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
- media generation control remains disabled until the project reaches `storyboard_ready`
- media submission returns HTTP 409 with a structured `planning_not_ready` error when called before scenes exist
- dashboard labels clearly distinguish planning jobs from media-generation jobs
- final video UI only becomes visible after the final MP4 endpoint confirms the file exists
- final video endpoint supports lightweight `HEAD` existence checks used by the dashboard without streaming the MP4

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
- API submission/status/list endpoints
- HTTP 202 submission semantics
- browser background-generation control
- media generation is gated until asynchronous planning has produced a storyboard
- premature media submission is reported as a resource-state conflict (`409`) rather than request validation failure (`422`)
- 2-second job polling and automatic artifact refresh on terminal state
- stale queued/running jobs are marked `interrupted` on process restart
- persistent local planning job manifests under `planning-jobs`
- planning worker uses one local worker to avoid competing for unified memory with media generation
- planning request validation is centralized in `app/job_api.py`; the unused duplicate planning router module was removed
- background job API helpers and response boundaries are explicitly typed for strict mypy
- web API helpers, dynamic JSON response boundaries, provider instances, and configuration access are explicitly typed for strict mypy
- media job listing avoids shadowing the `list` method name, eliminating a strict-mypy type resolution error
- job-manager collection annotations also avoid the class-level `list` method shadow
- strict mypy configuration keeps heavy optional ML packages out of the CI environment while preserving type checking of application boundaries
- corrected Python health-check field typing for strict mypy
- typed the optional LTX video provider
- corrected optional FFmpeg audio-asset lookup typing without changing render behavior
- corrected asynchronous web timeline JSON validation and separated image/video recovery result types
- structured-output repair now preserves the underlying JSON/schema failure cause after bounded retries
- script duration validation uses the model's explicit duration estimate as the Director contract
- generated scene status persistence uses the canonical `SceneStatus` enum
- CI installs FFmpeg/FFprobe so deterministic media QA tests run on GitHub-hosted Linux runners
- media orchestration tests create the required project manifest before lifecycle transitions
- subtitle tests explicitly cover deterministic max-character wrapping
- Ruff CI enforces correctness-oriented `E`, `F`, and `B` rules
- planning worker retries one failed Director run using persisted artifacts before marking the project failed
- structured-output validation failures preserve Pydantic field-level diagnostics for repair prompts and persisted job errors
- storyboard prompts minimize the LLM contract to required fields and let the application generate UUIDs
- storyboard outputs materialize canonical `scene-XXXX.json` manifests and `timeline.json` after validated planning
- resumed `storyboard_ready` projects revalidate storyboard timing against the project's target duration before accepting persisted output; stale/invalid timing forces storyboard regeneration instead of silently reusing it
- storyboard reconciliation now deterministically persists SRT and WebVTT subtitles from scene narration
- descriptive lifecycle logging now traces planning submission, configuration, Ollama health/model checks, Director stages, structured-output attempts/repairs, media job transitions, per-scene routing/generation, recovery/fallback decisions, progress and terminal outcomes
- logs intentionally record operational metadata (stage, model, counts, timings and errors) rather than full user prompts or generated media payloads
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
