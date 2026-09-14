# Local AI Video Generator — Detailed Engineering Plan

## Current implementation checkpoint

Phase 0–9 deterministic implementation is complete. **Phase 10 — Agentic Recovery and Refinement is in progress**, with bounded recovery foundation, project-level image/video recovery, targeted scene regeneration recovery, centralized video-provider construction, timing-safe video recovery refinement, and deterministic narration duration correction implemented. Target Apple M4 / 36 GB hardware acceptance remains a separate machine-level activity.

The detailed phased plan below is the source of truth and must stay synchronized with meaningful repository commits.

---

# 19. Phase 10 — Agentic Recovery and Refinement

**Status: IN PROGRESS — NARRATION CORRECTION INTEGRATED**

Recovery is explicitly finite and deterministic. Implemented `RecoveryPolicy`, `RecoveryResult`, and `run_bounded()` with zero-based attempt numbers supplied to each operation.

Current budgets:

```text
LLM:    3 total attempts (initial + 2 repairs)
Image:  3 total attempts (initial + 2 retries)
Video:  3 total attempts (initial + 2 retries)
Render: 2 total attempts (initial + 1 retry)
```

Project media orchestration invokes bounded image recovery when a scene has no image asset and bounded video recovery for image-to-video and image-motion generation. Targeted `regenerate-scene` uses the same bounded image/video recovery paths. Video recovery refines prompts without mutating canonical scene duration. Configured local video-provider construction is centralized and deterministic FFmpeg fallback construction is available from the provider factory.

Narration generation now applies deterministic pad-or-trim duration correction when synthesized audio differs materially from the canonical scene duration. The corrected artifact keeps its identity while its SHA-256 and duration metadata are updated.

Remaining Phase 10 increments:

1. Integrate hardened provider fallback policy everywhere and persist explicit fallback metadata.
2. Add bounded render recovery.
3. Complete Phase 10 acceptance and synchronize Phase 5–10 documentation.

---
