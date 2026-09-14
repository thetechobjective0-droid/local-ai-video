# Local AI Video Generator — Detailed Engineering Plan

## Current implementation checkpoint

Phase 0–9 deterministic implementation is complete. **Phase 10 — Agentic Recovery and Refinement is in progress**, with bounded recovery foundation, project-level image/video recovery, targeted scene regeneration recovery, centralized video-provider construction, timing-safe video recovery refinement, deterministic narration duration correction, deterministic provider fallback policy, and bounded final-render recovery implemented. Target Apple M4 / 36 GB hardware acceptance remains a separate machine-level activity.

The detailed phased plan below is the source of truth and must stay synchronized with meaningful repository commits.

---

# 19. Phase 10 — Agentic Recovery and Refinement

**Status: IN PROGRESS — FALLBACK + RENDER RECOVERY INTEGRATED**

Recovery is explicitly finite and deterministic. Implemented `RecoveryPolicy`, `RecoveryResult`, and `run_bounded()` with zero-based attempt numbers supplied to each operation.

Current budgets:

```text
LLM:    3 total attempts (initial + 2 repairs)
Image:  3 total attempts (initial + 2 retries)
Video:  3 total attempts (initial + 2 retries)
Render: 2 total attempts (initial + 1 retry)
```

Project media orchestration invokes bounded image recovery when a scene has no image asset and bounded video recovery for image-to-video and image-motion generation. Targeted `regenerate-scene` uses the same bounded image/video recovery paths. Video recovery refines prompts without mutating canonical scene duration. Configured local video-provider construction is centralized.

Narration generation applies deterministic pad-or-trim duration correction when synthesized audio differs materially from the canonical scene duration. Provider fallback is validated against the capability registry and persisted with primary/fallback provider identity and reason metadata. Final FFmpeg rendering has a bounded retry that removes only renderer-owned partial output before retrying and persists recovery strategy metadata in `render.json`.

Remaining Phase 10 work:

1. Repository-wide Phase 5–10 documentation synchronization.
2. Final acceptance review; target-machine model/performance acceptance remains explicitly external to CI.

---
