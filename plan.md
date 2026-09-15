# Local AI Video Generator — Complete Engineering Roadmap

Target: local-first AI video generation on Apple Silicon, initially Apple M4 / 36 GB unified memory.

## Architecture invariants

- Local inference and media processing only; no automatic cloud inference, uploads, telemetry, or remote processing.
- LLM proposes structured intent; deterministic application code validates, routes, executes, persists, QA-checks, and renders.
- Typed provider contracts isolate model/runtime implementations.
- Project-relative filesystem boundaries and safe FFmpeg argv construction are mandatory.
- Recovery is finite and policy-driven; no unbounded autonomous retries.
- Model weights, generated media, caches, secrets, and machine state are never committed.
- Heavy ML dependencies remain optional for normal CI.
- M4 resource concurrency is conservative by default.

## Phase status

| Phase | Scope | Status |
|---|---|---|
| 0 | Foundation, config, filesystem, resources, health/doctor | IMPLEMENTED; macOS memory probing hardened |
| 1 | Domain/project/scene/artifact contracts | IMPLEMENTED |
| 2 | Local Ollama Director, structured planning, resume | IMPLEMENTED; schema-constrained generation hardened |
| 3 | Local Diffusers image generation + MPS | IMPLEMENTED; M4 MODEL ACCEPTANCE; Accelerate is now an explicit image extra dependency; inference memory controls added |
| 4 | Local macOS TTS | IMPLEMENTED; integrated into media jobs with non-silent output validation |
| 5 | Timeline + SRT/WebVTT | IMPLEMENTED |
| 6 | Deterministic FFmpeg renderer + FFprobe validation | IMPLEMENTED; path containment hardened; macOS malloc diagnostic environment is sanitized for media subprocesses |
| 7 | Local AI I2V boundary + LTX provider + fallback | IMPLEMENTED; M4 MODEL ACCEPTANCE; inference memory controls added |
| 8 | Media routing, resources, caching, lifecycle | IMPLEMENTED; cache/resource expansion remains |
| 9 | Deterministic project/media QA | COMPLETE |
| 10 | Bounded recovery/refinement integrations | IMPLEMENTED; acceptance continues |
| 11 | Loopback FastAPI + browser dashboard | IMPLEMENTED; polling lifecycle race fixed, loading UX, stale-refresh, video readiness, and determinate progress UI hardened |
| 12 | Persistent planning/media jobs + restart semantics | IMPLEMENTED; stale planning-job recovery hardened; media jobs now finalize the project |
| 13 | Target-machine acceptance harness | IMPLEMENTED; real M4 acceptance remains an execution requirement |
| 14 | Semantic/visual evaluation | IMPLEMENTED baseline; deterministic alignment, continuity, narration, and storyboard consistency are covered; true model-based visual evaluation remains hardware/model acceptance work |
| 15 | Advanced recovery/refinement | IMPLEMENTED; bounded provider fallback/recovery paths are in place |
| 16 | Provider/model registry evolution | IMPLEMENTED; typed provider capability/factory boundaries are in place |
| 17 | Security/locality hardening | COMPLETE; filesystem/symlink containment, manifest validation, loopback serving, local Ollama enforcement, and security regression coverage hardened |
| 18 | Testing pyramid + CI/CD expansion | IMPLEMENTED; deterministic unit/integration/UI/security/migration/observability/CLI tests and CI quality gates are present; hardware acceptance remains outside CI |
| 19 | Observability/operational diagnostics | IMPLEMENTED; bounded in-process counters and duration summaries added without network telemetry |
| 20 | Persistence/schema migrations | IMPLEMENTED; idempotent storage migration upgrades legacy project manifests to schema 1.1 without touching media; migration is exposed through the operational CLI |
| 21 | M4 resource/performance optimization | IMPLEMENTED tooling; memory-efficient ML inference controls and acceptance resource measurements added; sustained thermal/GPU utilization and model-specific latency require target-machine runs |
| 22 | V1 production gate | IMPLEMENTED; deterministic locality/security/QA/semantic gate report added and exposed through the operational CLI |
| 23 | V2 advanced production features | IN PROGRESS; implementation scope and acceptance criteria defined; reproducibility manifest foundation added |
| 24 | V3 platform evolution/research | PLANNED; implementation scope and acceptance criteria defined |

## Current implementation state

Phases 0–22 have implementation coverage. Phase 23 is now in progress with its implementation contract documented and reproducibility metadata primitives added. Phase 24 has a defined research/platform contract and will follow the Phase 23 extension boundaries. Existing V1 invariants remain mandatory while V2/V3 capabilities are developed.

The repository must never claim the hardware gate passed from CI alone. Real model loading, generation, memory pressure, thermal behavior and output quality require the actual M4 machine.

Ruff 0.16.7 formatting is normalized across the previously failing application files; CI remains the authoritative execution path for lint, type checking, and tests. CI does not auto-commit formatting changes.

## Phase 23 — V2 Advanced Production Features

The detailed implementation contract is in `docs/phase-23-24.md`. The first foundation is `app/generation/reproducibility.py`, which captures immutable project/provider/model/parameter inputs and a deterministic fingerprint for future generation manifests, export/import, checkpointing, and benchmark comparison.

Next V2 implementation increments should build on this foundation: artifact integrity manifests, project export/import, dependency-aware resumable orchestration, scene-level regeneration, resource-aware scheduling, structured event history, advanced evaluation/refinement, and corresponding dashboard controls.

## Phase 24 — V3 Platform Evolution / Research

The detailed implementation contract is in `docs/phase-23-24.md`. Phase 24 remains sequenced after the Phase 23 provider/job extension points are stable. Its scope includes versioned provider capabilities, local benchmark/experiment reports, model compatibility discovery, multimodal/local evaluation research, performance experiments, and migration-safe platform evolution.

## Definition of done

Every phase requires implementation, deterministic tests where applicable, documentation, CI validation, explicit acceptance criteria, and target-machine validation whenever behavior depends on real hardware/model execution.

`plan.md` is the source of truth and must be updated after meaningful implementation commits.
