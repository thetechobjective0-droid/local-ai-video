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
- Native model-generated audio must remain synchronized with the generated video when the selected provider supplies it.

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
| 7 | Local AI I2V boundary + LTX provider + fallback | IMPLEMENTED; PyTorch LTX-Video retained and LTX-2.3 MLX added as the production Apple-Silicon temporal video + synchronized-audio path |
| 8 | Media routing, resources, caching, lifecycle | IMPLEMENTED; conservative resource scheduling now operational |
| 9 | Deterministic project/media QA | COMPLETE |
| 10 | Bounded recovery/refinement integrations | IMPLEMENTED |
| 11 | Loopback FastAPI + browser dashboard | IMPLEMENTED; polling, loading UX, stale refresh, progress, final-video readiness, and video-engine visibility hardened |
| 12 | Persistent planning/media jobs + restart semantics | IMPLEMENTED; checkpoints, resume, and cooperative cancellation/graceful shutdown added |
| 13 | Target-machine acceptance harness | IMPLEMENTED; real M4 hardware acceptance remains an execution requirement |
| 14 | Semantic/visual evaluation | IMPLEMENTED deterministic baseline plus bounded refinement proposals; true model-based visual evaluation remains optional research work |
| 15 | Advanced recovery/refinement | IMPLEMENTED |
| 16 | Provider/model registry evolution | IMPLEMENTED; versioned V3 provider registry added |
| 17 | Security/locality hardening | COMPLETE |
| 18 | Testing pyramid + CI/CD expansion | IMPLEMENTED; deterministic quality gates remain authoritative |
| 19 | Observability/operational diagnostics | IMPLEMENTED; structured event history extends local diagnostics |
| 20 | Persistence/schema migrations | IMPLEMENTED; schema 1.1 migration path present |
| 21 | M4 resource/performance optimization | IMPLEMENTED tooling; target-machine profiling remains hardware-specific |
| 22 | V1 production gate | IMPLEMENTED |
| 23 | V2 advanced production features | IMPLEMENTED; reproducibility, integrity/archive, dependency checkpoints, resumable/cancellable jobs, selective scene regeneration, memory-aware scheduling, structured event history, scene/timeline editing, per-scene narration/voice controls, transition/subtitle metadata, approval checkpoints, operator APIs, bounded evaluation/refinement, and local dashboard integration surfaces completed |
| 24 | V3 platform evolution/research | IMPLEMENTED platform foundation; versioned provider discovery, compatibility checks, local benchmark history, reproducible experiment manifests/results, benchmark comparison reporting, and loopback APIs completed |

## Current implementation state

The repository contains the complete V2/V3 application architecture described by `docs/phase-23-24.md` while preserving the V1 local-only invariants. The video path has now been corrected based on real output inspection: the production default is no longer a still-image animation path and no longer relies on PyTorch LTX-Video alone.

`ltx2_mlx` is now the default Apple-Silicon video provider. It invokes the separately prepared local `dgrauet/ltx-2-mlx` runtime with `uv run --offline`, uses the local LTX-2.3 q8 model pack, accepts the storyboard image as I2V conditioning, uses the recommended two-stage pipeline with low-memory streaming, generates real temporal frames, and preserves synchronized native audio by extracting the generated MP4 audio track into the scene audio artifact. Real AI artifacts are tagged `generation_mode=ai_i2v` and `temporal_generation=true` and are contract-validated before acceptance.

`run.sh` is now the one-command setup path on the target M4: it validates macOS arm64 prerequisites, syncs the application and local MLX runtime, structurally verifies the expected `ltx-2-mlx` package and console-script layout, and detects the q8 model pack. When the model pack is absent it interactively offers to download `dgrauet/ltx-2.3-mlx-q8` into the configured local model directory; `LTX_AUTO_DOWNLOAD_MODEL=yes|no` provides non-interactive control. The setup no longer executes the external CLI as a health probe, avoiding false negatives from runtime import/help behavior while leaving the actual `ltx-2-mlx generate` invocation as the authoritative execution path. All model/runtime assets remain uncommitted local state.

The storyboard prompt now keeps real-video scenes in the 5–10 second range and asks for concrete temporal actions instead of merely static visual descriptions. Longer projects are represented by more scenes. Strict I2V routing prevents unsupported durations or memory conditions from silently degrading to static/Ken-Burns media. Deterministic FFmpeg motion remains explicit-only.

The browser dashboard remains the primary workflow and identifies the generated scene mode. LTX-2.3 MLX setup and operational requirements are documented in `docs/ltx2-mlx.md`; model weights and external runtime assets remain uncommitted local state.

The remaining validation items are target-machine execution claims that cannot be established from repository code alone: sustained Apple M4 thermal behavior, model-specific latency/throughput, and real LTX-2.3 MLX workload acceptance. These are execution/acceptance activities rather than missing software architecture.

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
- Real temporal I2V as the default scene-video contract with explicit deterministic fallback semantics.
- Native synchronized audio persistence for multimodal video providers.

## Phase 24 — V3 Platform Evolution / Research

Implemented platform foundation:
- `app/platform/registry.py`: versioned provider descriptors and capability compatibility discovery.
- `app/platform/benchmarks.py`: local machine-readable environment benchmark history and shared-measurement comparison/regression reporting.
- `app/platform/experiments.py`: provider/version/parameter/seed experiment manifests and result records.
- `app/platform_api.py`: provider discovery, compatibility, benchmark history/comparison, and experiment HTTP APIs.
- `docs/platform-v3.md`: V3 architecture and operational contract.
- `docs/video-quality.md`: local AI-video quality configuration and tuning guide.
- `docs/ltx2-mlx.md`: LTX-2.3 MLX Apple-Silicon runtime setup and audio/video contract.
- `tests/unit/test_v3_platform.py`: provider, experiment, and benchmark-comparison coverage.
- `tests/unit/test_ltx2_mlx_video.py`: deterministic LTX-2 MLX provider contract coverage.

The platform intentionally does not make network access mandatory. Model-specific multimodal evaluation, quantization research, thermal policies, and new providers can now be added behind these stable extension contracts without modifying the core orchestration path.

## Definition of done

Every phase requires implementation, deterministic tests where applicable, documentation, CI validation, explicit acceptance criteria, and target-machine validation whenever behavior depends on real hardware/model execution.

`plan.md` is the source of truth and must be updated after meaningful implementation commits.
