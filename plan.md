# Local AI Video Generator — Detailed Engineering Plan

## Current implementation checkpoint

**Phases 0–10 repository implementation are complete. Phase 11 is now in progress.** The Phase 11 web layer is being built as a thin local-only interface over the existing Director, media generation, QA, recovery, timeline, and renderer services. The API/UI must not duplicate generation logic. Target Apple M4 / 36 GB hardware acceptance remains a machine-level activity for actual model loading, memory pressure, generation latency, thermal behavior, and subjective visual quality.

The detailed phased plan below is the source of truth and must stay synchronized with meaningful repository commits.

---

# 19. Phase 10 — Agentic Recovery and Refinement

**Status: COMPLETE — BOUNDED LOCAL RECOVERY**

Recovery is finite, deterministic, auditable, and local-only. Implemented `RecoveryPolicy`, `RecoveryResult`, and `run_bounded()` with explicit retry budgets.

Current budgets:

```text
LLM:    3 total attempts (initial + 2 repairs)
Image:  3 total attempts (initial + 2 retries)
Video:  3 total attempts (initial + 2 retries)
Render: 2 total attempts (initial + 1 retry)
```

Delivered through Phase 10:

- bounded image recovery with deterministic prompt refinement
- bounded video recovery with timing-safe prompt refinement that never mutates canonical scene timing
- recovery in project media orchestration and targeted scene regeneration
- centralized configured video-provider construction
- capability-validated deterministic FFmpeg fallback
- explicit fallback provider/model/reason metadata
- deterministic narration pad-or-trim duration correction
- bounded final-render retry with renderer-owned partial-output cleanup
- persisted recovery metadata in scene and render manifests
- configured image-generation settings propagated into project media generation
- targeted regeneration invalidates final/render/QA artifacts before regeneration
- synchronized Phase 5–10 status documentation
- no unused recovery wrapper retained in the render package

## Acceptance boundary

CI remains responsible for repository validation. Target-machine acceptance is intentionally separate: the actual Apple M4 / 36 GB Mac must load the configured local models and measure memory pressure, generation latency, thermal behavior, and visual output quality before those hardware-specific claims can be marked accepted.

---

# 20. Phase 11 — Local Web API + UI

**Status: IN PROGRESS — API FOUNDATION**

### Delivered

- created `phase11-web-api` branch from the Phase 10 implementation line
- added a localhost-oriented FastAPI application entry point
- added project listing and project-detail endpoints
- added project creation and Director resume endpoints
- added deterministic project QA endpoint with persisted `qa-report.json`
- added final MP4 artifact endpoint
- added scene video regeneration endpoint using existing bounded recovery
- kept API orchestration thin and delegated to existing application services

### Remaining

- add FastAPI dependency/packaging configuration
- add API error handling and request validation hardening
- add local web UI/dashboard
- add project creation form and generation controls
- add scene/storyboard and artifact views
- add QA display and targeted regeneration controls
- add API/UI documentation and launch command
- add Phase 11 acceptance/status documentation

### Acceptance target

```text
Browser -> localhost web UI -> local API -> existing application services
                                      -> project/artifact store
```

The web layer must remain local-only, artifact-first, resumable, and provider-agnostic. No cloud inference, upload, telemetry, or duplicated generation logic is permitted.
