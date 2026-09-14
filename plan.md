# Local AI Video Generator — Detailed Engineering Plan

## Current implementation checkpoint

Phase 0–8 are substantially implemented. **Phase 9 deterministic quality assurance is complete**, including project QA reporting, targeted scene regeneration, image/audio/video integrity validation, audio loudness/silence gates, timeline/subtitle validation, and final-video validation. **Phase 10 — Agentic Recovery and Refinement is now in progress**, with bounded recovery foundation and project-level image/video recovery integration implemented. Target Apple M4 / 36 GB hardware acceptance remains a separate machine-level acceptance activity.

The detailed phased plan below is the source of truth and must stay synchronized with meaningful repository commits.

---

# 19. Phase 10 — Agentic Recovery and Refinement

**Status: IN PROGRESS — ORCHESTRATOR RECOVERY INTEGRATED**

Recovery is explicitly finite and deterministic. Implemented `RecoveryPolicy`, `RecoveryResult`, and `run_bounded()` with zero-based attempt numbers supplied to each operation.

Current budgets:

```text
LLM:    3 total attempts (initial + 2 repairs)
Image:  3 total attempts (initial + 2 retries)
Video:  3 total attempts (initial + 2 retries)
Render: 2 total attempts (initial + 1 retry)
```

Project media orchestration now invokes bounded image recovery when a scene has no image asset and bounded video recovery for image-to-video and image-motion generation. Recovery metadata is persisted into scene metadata with attempt counts and deterministic strategies. Existing provider fallback remains available after bounded video recovery fails.

Next Phase 10 increments:

1. Integrate recovery into targeted regeneration paths.
2. Strengthen provider fallback policy and record fallback metadata.
3. Add narration duration correction.
4. Add bounded render recovery.
5. Complete Phase 10 acceptance.

---
