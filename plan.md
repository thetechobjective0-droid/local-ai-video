# Local AI Video Generator — Detailed Engineering Plan

## Current implementation checkpoint

**Phases 0–10 repository implementation are complete.** Phases 5–10 status documents have been synchronized with the implemented code. The remaining acceptance boundary is machine-level validation on the target Apple M4 / 36 GB system for actual model loading, memory pressure, generation latency, and subjective visual quality; these cannot honestly be completed from CI or this repository-only environment.

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
- bounded video recovery with timing-safe prompt refinement
- recovery in project media orchestration and targeted scene regeneration
- centralized configured video-provider construction
- capability-validated deterministic FFmpeg fallback
- explicit fallback provider/model/reason metadata
- deterministic narration pad-or-trim duration correction
- bounded final-render retry with partial-output cleanup
- persisted recovery metadata in scene and render manifests
- synchronized Phase 5–10 documentation

## Acceptance boundary

CI remains responsible for repository validation. Target-machine acceptance is intentionally separate: the actual Apple M4 / 36 GB Mac must load the configured local models and measure memory pressure, generation latency, thermal behavior, and visual output quality before those hardware-specific claims can be marked accepted.

---
