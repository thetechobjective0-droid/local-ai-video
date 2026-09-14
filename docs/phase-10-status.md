# Phase 10 — Agentic Recovery and Refinement

## Status

**IN PROGRESS — BOUNDED RECOVERY FOUNDATION**

Phase 10 introduces explicit, finite recovery policies around generation operations. The first increment establishes reusable recovery primitives without allowing unbounded autonomous retries or policy changes.

## Implemented

- `RecoveryPolicy` with explicit maximum attempts.
- `run_bounded()` with deterministic zero-based attempt numbers.
- Dedicated retry budgets for LLM repair, image generation, video generation, and rendering.
- Final retryable failure is propagated; failures are never converted into false success.
- Python 3.11-compatible generic result model.

Current policy budgets:

```text
LLM:    3 total attempts (initial + 2 repairs)
Image:  3 total attempts (initial + 2 retries)
Video:  3 total attempts (initial + 2 retries)
Render: 2 total attempts (initial + 1 retry)
```

## Safety boundary

Recovery does not change provider selection, local-only policy, filesystem boundaries, or resource limits. Future refinements may simplify prompts or reduce media settings only through explicit deterministic policies.

## Next

1. Integrate bounded recovery into scene image/video generation.
2. Add deterministic prompt/settings refinement between attempts.
3. Integrate narration duration correction.
4. Add bounded render recovery.
5. Persist recovery attempt metadata.
6. Complete Phase 10 acceptance.
