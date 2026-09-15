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
| 23 | V2 advanced production features | IN PROGRESS; reproducibility, artifact-integrity, export/import, dependency-aware checkpoints, persistent job resume, selective scene regeneration, resource-aware scheduling, and structured event history implemented |
| 24 | V3 platform evolution/research | PLANNED; implementation scope and acceptance criteria defined |

## Current implementation state

Phases 0–22 have implementation coverage. Phase 23 is in progress with reproducibility, artifact-integrity, portable project archive, dependency-aware checkpoints, reusable checkpoint runtime, persistent media-job checkpoint integration, selective scene regeneration, resource-aware scheduling, and append-only structured job event history. Scene regeneration invalidates stale scene/downstream artifacts and media/finalization checkpoints, clears stale scene references, regenerates required downstream media, and rebuilds the final project. Media jobs now use conservative local memory admission based on provider memory class and current macOS resource availability, with heavyweight providers serialized by policy and queued jobs released when memory becomes available. Portable archive import/export is compatible with Python 3.11, rejects unsafe links/device members, and verifies the persisted integrity manifest correctly. Every checkpoint stage can now record start/skip/block/complete events, and the resource-aware worker records admission/release and terminal job events. Event history is local-only JSONL, bounded on replay, and diagnostic failures cannot interrupt media execution. Phase 24 has a defined research/platform contract and will follow the Phase 23 extension boundaries. Existing V1 invariants remain mandatory while V2/V3 capabilities are developed.

## Phase 23 — V2 Advanced Production Features

The detailed contract is in `docs/phase-23-24.md`.

Implemented foundations:
- `app/generation/reproducibility.py`: immutable project/provider/model/parameter capture and deterministic fingerprinting.
- `app/storage/integrity.py`: SHA-256 artifact manifests, size tracking, project-relative containment checks, atomic persistence, and verification.
- `app/storage/archive.py`: portable project export/import with archive path validation, Python 3.11-safe extraction, unsafe-member rejection, and integrity verification.
- `app/orchestrator/checkpoints.py`: crash-safe stage checkpoints, dependency readiness, sequence tracking, completed-artifact tracking, and terminal-state validation.
- `app/orchestrator/checkpoint_runtime.py`: reusable stage lifecycle for loading, starting, completing, skipping already-completed stages, and event emission.
- `app/orchestrator/events.py`: versioned append-only local JSONL job history with sequence numbers, bounded replay, and malformed-record tolerance.
- `app/orchestrator/jobs.py`: durable audio/media/finalization stage checkpoints and explicit interrupted/failed job resume.
- `app/orchestrator/regeneration.py`: dependency-aware invalidation of scene artifacts, final outputs, evaluation artifacts, and stale media/finalization checkpoints.
- `app/job_api.py`: selective scene regeneration route with downstream regeneration and deterministic finalization.
- `app/orchestrator/resource_scheduler.py`: local memory admission control, reservation accounting, provider memory classes, and conservative high-memory concurrency limits.
- `app/orchestrator/scheduled_jobs.py`: resource-aware media worker wrapper with queued admission and reservation release, plus structured resource/job lifecycle events.
- `tests/unit/test_job_events.py`: deterministic coverage for event sequencing, bounded replay, and malformed-record tolerance.

Next increments remain advanced evaluation/refinement and dashboard resume/regeneration/resource/event-history controls.

## Phase 24 — V3 Platform Evolution / Research

The detailed contract is in `docs/phase-23-24.md`. Phase 24 remains sequenced after Phase 23 provider/job extension points are stable. Its scope includes versioned provider capabilities, local benchmark/experiment reports, model compatibility discovery, multimodal/local evaluation research, performance experiments, and migration-safe platform evolution.

## Definition of done

Every phase requires implementation, deterministic tests where applicable, documentation, CI validation, explicit acceptance criteria, and target-machine validation whenever behavior depends on real hardware/model execution.

`plan.md` is the source of truth and must be updated after meaningful implementation commits.
