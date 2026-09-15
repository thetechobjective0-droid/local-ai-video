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
- A real AI video run must use a temporal I2V provider; deterministic still-image motion is never an implicit substitute.

## Phase status

| Phase | Scope | Status |
|---|---|---|
| 0 | Foundation, config, filesystem, resources, health/doctor | IMPLEMENTED; macOS memory probing hardened |
| 1 | Domain/project/scene/artifact contracts | IMPLEMENTED |
| 2 | Local Ollama Director, structured planning, resume | IMPLEMENTED; schema-constrained generation hardened |
| 3 | Local Diffusers image generation + MPS | IMPLEMENTED; M4 MODEL ACCEPTANCE; Accelerate explicit image dependency; inference memory controls added |
| 4 | Local macOS TTS | IMPLEMENTED; non-silent output validation integrated |
| 5 | Timeline + SRT/WebVTT | IMPLEMENTED |
| 6 | Deterministic FFmpeg renderer + FFprobe validation | IMPLEMENTED; path containment and macOS media-process environment hardened |
| 7 | Local AI I2V boundary + LTX provider + fallback | IMPLEMENTED; real LTX I2V is now the default production provider, routing prioritizes I2V, quality controls are provider-bound, and FFmpeg fallback is explicit opt-in only |
| 8 | Media routing, resources, caching, lifecycle | IMPLEMENTED; conservative resource scheduling now operational |
| 9 | Deterministic project/media QA | COMPLETE |
| 10 | Bounded recovery/refinement integrations | IMPLEMENTED |
| 11 | Loopback FastAPI + browser dashboard | IMPLEMENTED; polling, loading UX, stale refresh, progress, and final-video readiness hardened |
| 12 | Persistent planning/media jobs + restart semantics | IMPLEMENTED; checkpoints, resume, and cooperative cancellation/graceful shutdown added |
| 13 | Target-machine acceptance harness | IMPLEMENTED; real M4 acceptance remains an execution requirement |
| 14 | Semantic/visual evaluation | IMPLEMENTED deterministic baseline plus bounded refinement proposals; true model-based visual evaluation remains optional research work |
| 15 | Advanced recovery/refinement | IMPLEMENTED |
| 16 | Provider/model registry evolution | IMPLEMENTED; versioned V3 provider registry added |
| 17 | Security/locality hardening | COMPLETE |
| 18 | Testing pyramid + CI/CD expansion | IMPLEMENTED; deterministic quality gates remain authoritative |
| 19 | Observability/operational diagnostics | IMPLEMENTED; structured event history extends local diagnostics |
| 20 | Persistence/schema migrations | IMPLEMENTED; schema 1.1 migration path present |
| 21 | M4 resource/performance optimization | IMPLEMENTED tooling; target-machine profiling remains hardware-specific |
| 22 | V1 production gate | IMPLEMENTED |
| 23 | V2 advanced production features | IMPLEMENTED; reproducibility, integrity/archive, dependency checkpoints, resumable/cancellable jobs, selective regeneration, memory-aware scheduling, structured event history, scene/timeline editing, per-scene narration/voice controls, transition/subtitle metadata, approval checkpoints, operator APIs, bounded evaluation/refinement, and local dashboard integration surfaces completed |
| 24 | V3 platform evolution/research | IMPLEMENTED platform foundation; versioned provider discovery, compatibility checks, local benchmark history, reproducible experiment manifests/results, benchmark comparison reporting, and loopback APIs completed |

## Current implementation state

The repository now contains the complete V2/V3 application architecture described by `docs/phase-23-24.md` while preserving the V1 local-only invariants. Phase 23 has durable reproducibility and integrity metadata, portable Python 3.11-safe archives, dependency-aware checkpoints, resumable and cooperatively cancellable media jobs, memory-aware scheduling, structured local JSONL job events, selective scene regeneration, editable scene timing/order/narration/visual prompts, per-scene voice metadata consumed by macOS TTS, transition metadata consumed by timeline resolution, subtitle metadata, human approval records, deterministic evaluation/refinement proposals, and local operator APIs. Phase 24 adds a versioned provider registry, capability compatibility discovery, local benchmark reports, reproducible experiment manifests/results, benchmark comparison/regression reporting, and loopback APIs for platform operations.

The video-generation path has been corrected so the application now treats real local temporal generation as the production path. `LTXImageToVideoPipeline` is the default configured video provider, scene routing prioritizes `IMAGE_TO_VIDEO` whenever the provider supports it, and LTX receives the configured inference/guidance/conditioning controls from the provider factory instead of silently reverting to hard-coded defaults. Generated LTX artifacts are tagged `generation_mode=ai_i2v` and `temporal_generation=true`. `ffmpeg_ken_burns` is explicitly documented and identified as still-image motion (`generation_mode=image_motion`) and can only be used as a primary provider or an operator-enabled fallback; an LTX failure no longer silently becomes a slideshow-like clip.

The previous acceptance video exposed the architectural problem: the default application path could render multiple still images with FFmpeg motion rather than synthesizing temporal frames. That behavior is now blocked by the default configuration and routing rules. A fresh project using the default configuration requires the local LTX model; deterministic motion must be selected intentionally.

The remaining validation items are target-machine execution claims that cannot be established from repository code alone: sustained Apple M4 thermal behavior, model-specific latency/throughput, and real Diffusers/LTX workload acceptance. Those are execution/acceptance activities rather than missing software architecture.

## Phase 23 — V2 Advanced Production Features

The detailed contract is in `docs/phase-23-24.md`.

Implemented:
- Reproducibility manifests and deterministic fingerprints.
- SHA-256 artifact integrity manifests and verification.
- Portable export/import with unsafe archive-member rejection and Python 3.11 compatibility.
- Dependency-aware checkpoints and reusable checkpoint runtime.
- Persistent media-job resume and cooperative cancellation/graceful shutdown primitives.
- Selective scene regeneration with downstream invalidation.
- Resource-aware unified-memory scheduling and cancellation-aware admission.
- Append-only versioned JSONL event history and operator resource/event endpoints.
- Scene editing and reorder, with duration/timing validation.
- Per-scene narration and voice metadata with voice override consumed by TTS.
- Transition and subtitle metadata with transition consumed by timeline resolution.
- Human approval checkpoint records and API controls.
- Deterministic evaluation plus bounded, non-autonomous refinement proposals.
- Existing dashboard controls for scene inspection, regeneration, resume, QA, progress, and final-video readiness.
- Real LTX I2V as the default scene-video path with explicit deterministic FFmpeg fallback semantics.

## Phase 24 — V3 Platform Evolution / Research

Implemented platform foundation:
- `app/platform/registry.py`: versioned provider descriptors and capability compatibility discovery.
- `app/platform/benchmarks.py`: local machine-readable environment benchmark history and shared-measurement comparison/regression reporting.
- `app/platform/experiments.py`: provider/version/parameter/seed experiment manifests and result records.
- `app/platform_api.py`: provider discovery, compatibility, benchmark history/comparison, and experiment HTTP APIs.
- `docs/platform-v3.md`: V3 architecture and operational contract.
- `docs/video-quality.md`: local AI-video quality configuration and tuning guide.
- `tests/unit/test_v3_platform.py`: provider, experiment, and benchmark-comparison coverage.

The platform intentionally does not make network access mandatory. Model-specific multimodal evaluation, quantization research, thermal policies, and new providers can now be added behind these stable extension contracts without modifying the core orchestration path.

## Definition of done

Every phase requires implementation, deterministic tests where applicable, documentation, CI validation, explicit acceptance criteria, and target-machine validation whenever behavior depends on real hardware/model execution.

`plan.md` is the source of truth and must be updated after meaningful implementation commits.
