# Local AI Video Generator — Detailed Engineering Plan

## Current implementation checkpoint

Phase 0–8 are substantially implemented. **Phase 9 deterministic quality assurance is complete**, including project QA reporting, targeted scene regeneration, image/audio/video integrity validation, audio loudness/silence gates, timeline/subtitle validation, and final-video validation. **Phase 10 — Agentic Recovery and Refinement is now in progress**, with bounded recovery foundation, project-level image/video recovery, and targeted scene regeneration recovery integrated. Target Apple M4 / 36 GB hardware acceptance remains a separate machine-level acceptance activity.

The detailed phased plan below is the source of truth and must stay synchronized with meaningful repository commits.

---

# 19. Phase 10 — Agentic Recovery and Refinement

**Status: IN PROGRESS — TARGETED REGENERATION RECOVERY INTEGRATED**

Recovery is explicitly finite and deterministic. Implemented `RecoveryPolicy`, `RecoveryResult`, and `run_bounded()` with zero-based attempt numbers supplied to each operation.

Current budgets:

```text
LLM:    3 total attempts (initial + 2 repairs)
Image:  3 total attempts (initial + 2 retries)
Video:  3 total attempts (initial + 2 retries)
Render: 2 total attempts (initial + 1 retry)
```

Project media orchestration invokes bounded image recovery when a scene has no image asset and bounded video recovery for image-to-video and image-motion generation. Targeted `regenerate-scene` now uses the same bounded image/video recovery paths and records recovery metadata. Video recovery failure can fall back to the deterministic FFmpeg motion provider when the configured provider is not already FFmpeg.

Next Phase 10 increments:

1. Strengthen provider fallback policy and record fallback metadata.
2. Add narration duration correction.
3. Add bounded render recovery.
4. Complete Phase 10 acceptance.

---
