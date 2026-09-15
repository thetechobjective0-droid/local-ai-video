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
| 11 | Loopback FastAPI + browser dashboard | IMPLEMENTED; polling, loading UX, stale-refresh, video readiness, and determinate progress UI hardened |
| 12 | Persistent planning/media jobs + restart semantics | IMPLEMENTED; stale planning-job recovery hardened; media jobs now finalize the project |
| 13 | Target-machine acceptance harness | IMPLEMENTED; real M4 run pending |
| 14 | Semantic/visual evaluation | IN PROGRESS; deterministic alignment, continuity, narration, and storyboard consistency baselines added |
| 15 | Advanced recovery/refinement | IMPLEMENTED; bounded provider fallback/recovery paths are in place |
| 16 | Provider/model registry evolution | IMPLEMENTED; typed provider capability/factory boundaries are in place |
| 17 | Security/locality hardening | COMPLETE; filesystem/symlink containment, manifest validation, loopback serving, local Ollama enforcement, and security regression coverage hardened |
| 18 | Testing pyramid + CI/CD expansion | PARTIALLY IMPLEMENTED; deterministic unit/integration/UI/security/migration/observability/CLI tests added; hardware acceptance remains outside CI |
| 19 | Observability/operational diagnostics | IMPLEMENTED; bounded in-process counters and duration summaries added without network telemetry |
| 20 | Persistence/schema migrations | IMPLEMENTED; idempotent storage migration upgrades legacy project manifests to schema 1.1 without touching media; migration is now exposed through the operational CLI |
| 21 | M4 resource/performance optimization | IN PROGRESS; memory-efficient ML inference controls and acceptance resource measurements added |
| 22 | V1 production gate | IMPLEMENTED; deterministic locality/security/QA/semantic gate report added and exposed through the operational CLI |
| 23 | V2 advanced production features | FUTURE |
| 24 | V3 platform evolution/research | FUTURE |

## Current implementation state

Phases 0–13 are implemented. Phase 14 has a deterministic semantic baseline. Phases 15–17 and 19–20 now have production-oriented implementation primitives, and Phase 22 has a deterministic V1 gate. The target Mac runtime has macOS-safe memory probing, demand-driven ML provider construction, bounded recovery, safe artifact containment, loopback-only inference, deterministic QA, semantic baseline evaluation, local observability, and idempotent schema migration. The dashboard has a visible operation loader, determinate planning/media progress bars, correct polling lifecycle, final-video readiness handling, and terminal-state refresh. Diffusers/LTX inference uses memory-pressure controls and acceptance records process resource metrics. External media subprocesses use sanitized environments. The `video-agent` entry point now also exposes `migrate` and `production-gate` operational commands.

The repository must never claim the hardware gate passed from CI alone. Real model loading, generation, memory pressure, thermal behavior and output quality require the actual M4 machine.

The latest CI formatting regression is being normalized against Ruff 0.16.7 before the next full CI validation; no formatter auto-commit is used in CI. Evaluation, production-gate, FFmpeg, security, and filesystem formatting have now been normalized.

## Phase 14 — Semantic / visual evaluation

`app/evaluation.py` provides deterministic project-prompt alignment, adjacent-scene continuity, visual-description-to-narration alignment, and image-prompt-to-motion-prompt storyboard consistency. These are lexical heuristics and are explicitly not visual understanding.

Remaining work is true local image/scene semantic evaluation, I2V motion quality, stronger visual continuity, final-video evaluation, and an optional local-model evaluator behind a provider boundary.

## Phase 17 — Security/locality hardening

Security hardening is complete. `FilesystemStore.resolve_path()` and `project_path()` provide the containment boundary; media endpoints validate typed manifests, ownership and artifact types; loopback serving and Ollama endpoint validation enforce locality; subprocess invocation remains argv-based without shell execution; and security regression tests cover traversal, symlink, endpoint and manifest boundaries.

## Phase 19 — Observability / operational diagnostics

`app/observability.py` provides bounded in-process counters, bounded duration observations, timer context management, and serializable summaries. Counter names and duration series are capped to prevent an accidental unbounded-memory growth path. It intentionally performs no network telemetry. This is the base layer for integrating per-job/per-provider metrics into operational reports.

## Phase 20 — Persistence / schema migrations

`app/storage/migrations.py` provides an idempotent filesystem migration entry point. Legacy `project.json` manifests are upgraded to schema `1.1` atomically while generated media remains untouched. Re-running the migration is a no-op. The `video-agent migrate` command makes the operation explicit and repeatable.

## Phase 21 — M4 resource/performance optimization

The ML providers reduce inference memory pressure through capability-gated attention/VAE slicing and tiling, `torch.inference_mode()`, explicit temporary reference release, and accelerator/Python cache cleanup. Acceptance records peak process RSS, CPU seconds, stage wall-clock timings, and before/after resource snapshots. CPU/GPU utilization, sustained thermal behavior, and model-specific latency still require target-machine runs.

## Phase 22 — V1 production gate

`app/production_gate.py` evaluates a persisted project against the local-only policy, schema version, storage security audit, deterministic media QA, and semantic baseline. It produces a machine-readable gate report and does not claim target-hardware acceptance. The `video-agent production-gate PROJECT_ID` command exposes the check operationally; the real M4 acceptance command remains the hardware gate.

## Definition of done

Every phase requires implementation, deterministic tests where applicable, documentation, CI validation, explicit acceptance criteria, and target-machine validation whenever behavior depends on real hardware/model execution.

`plan.md` is the source of truth and must be updated after meaningful implementation commits.
