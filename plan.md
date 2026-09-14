# Local AI Video Generator — Detailed Engineering Plan

## Current implementation checkpoint

Phase 0–8 are substantially implemented. **Phase 9 deterministic quality assurance is complete**, including project QA reporting, targeted scene regeneration, image/audio/video integrity validation, audio loudness/silence gates, timeline/subtitle validation, and final-video validation. **Phase 10 — Agentic Recovery and Refinement is now in progress**, with bounded recovery foundation plus deterministic image and video recovery implemented. Target Apple M4 / 36 GB hardware acceptance remains a separate machine-level acceptance activity.

The detailed phased plan below is the source of truth and must stay synchronized with meaningful repository commits.

---

# 19. Phase 10 — Agentic Recovery and Refinement

**Status: IN PROGRESS — IMAGE + VIDEO RECOVERY INTEGRATED**

Recovery is explicitly finite and deterministic. Implemented `RecoveryPolicy`, `RecoveryResult`, and `run_bounded()` with zero-based attempt numbers supplied to each operation.

Current budgets:

```text
LLM:    3 total attempts (initial + 2 repairs)
Image:  3 total attempts (initial + 2 retries)
Video:  3 total attempts (initial + 2 retries)
Render: 2 total attempts (initial + 1 retry)
```

Image recovery wraps scene image generation in the image retry budget and applies deterministic refinement: original prompt, normalized/truncated prompt, then visual-description fallback.

Video recovery wraps scene video generation in the video retry budget and deterministically reduces requested duration on later attempts (100%, 75%, then 50%, with a 1-second floor). It preserves the provider boundary and surfaces failure after the finite budget rather than fabricating success.

Next Phase 10 increments:

1. Integrate recovery wrappers into the project orchestrator and targeted regeneration paths.
2. Add deterministic video provider fallback where capability policy permits.
3. Add narration duration correction.
4. Add bounded render recovery.
5. Persist recovery attempt metadata across stages.
6. Complete Phase 10 acceptance.

---
