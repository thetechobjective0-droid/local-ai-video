# Local AI Video Generator — Detailed Engineering Plan

## Current implementation checkpoint

**Phases 0–10 repository implementation are complete.** Phases 5–10 status documents are synchronized with the implemented code, including timeline/subtitles, rendering, AI video provider integration, deterministic media strategy, deterministic QA, and bounded recovery/refinement. The final hardening also ensures project media orchestration receives configured image-generation parameters and targeted regeneration invalidates downstream final-render artifacts. Target Apple M4 / 36 GB hardware acceptance remains a machine-level activity for actual model loading, memory pressure, generation latency, thermal behavior, and subjective visual quality.

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
