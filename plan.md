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
| 0 | Foundation, config, filesystem, resources, health/doctor | IMPLEMENTED |
| 1 | Domain/project/scene/artifact contracts | IMPLEMENTED |
| 2 | Local Ollama Director, structured planning, resume | IMPLEMENTED |
| 3 | Local Diffusers image generation + MPS | IMPLEMENTED; M4 MODEL ACCEPTANCE |
| 4 | Local macOS TTS | IMPLEMENTED |
| 5 | Timeline + SRT/WebVTT | IMPLEMENTED |
| 6 | Deterministic FFmpeg renderer + FFprobe validation | IMPLEMENTED; path containment hardened |
| 7 | Local AI I2V boundary + LTX provider + fallback | IMPLEMENTED; M4 MODEL ACCEPTANCE |
| 8 | Media routing, resources, caching, lifecycle | IMPLEMENTED; cache/resource expansion remains |
| 9 | Deterministic project/media QA | COMPLETE |
| 10 | Bounded recovery/refinement integrations | IMPLEMENTED; acceptance continues |
| 11 | Loopback FastAPI + browser dashboard | IMPLEMENTED |
| 12 | Persistent planning/media jobs + restart semantics | IMPLEMENTED; stale planning-job recovery hardened |
| 13 | Target-machine acceptance harness | IMPLEMENTED; real M4 run pending |
| 14 | Semantic/visual evaluation | IN PROGRESS; deterministic semantic baseline added |
| 15 | Advanced recovery/refinement | PLANNED |
| 16 | Provider/model registry evolution | PLANNED |
| 17 | Security/locality hardening | IN PROGRESS; renderer/job containment + restart recovery hardened |
| 18 | Testing pyramid + CI/CD expansion | PARTIALLY IMPLEMENTED; acceptance/restart/evaluation tests added |
| 19 | Observability/operational diagnostics | PARTIALLY IMPLEMENTED |
| 20 | Persistence/schema migrations | PLANNED |
| 21 | M4 resource/performance optimization | PLANNED; depends on measurements |
| 22 | V1 production gate | PLANNED |
| 23 | V2 advanced production features | FUTURE |
| 24 | V3 platform evolution/research | FUTURE |

## Implemented foundation: Phases 0–13

The repository contains the validated local Director pipeline, typed domain contracts, local Ollama integration, Diffusers image generation, macOS Speech narration, deterministic timelines/subtitles, FFmpeg rendering, LTX image-to-video integration, deterministic media routing/fallback, content-addressed scene-video caching, deterministic QA, bounded recovery, loopback web UI/API, persistent JSON-backed planning/media jobs, progress reporting, restart recovery, final-video gating, target-machine acceptance reporting, renderer path containment, and stale planning-job recovery.

## Phase 13 — Target-machine acceptance harness

`app/acceptance.py` provides local-only/platform/tool/model readiness checks, MPS readiness, model-load timing, real scene image/video generation timing, before/after resource snapshots, deterministic project QA, final FFmpeg render/final QA, and a machine-readable JSON report.

```bash
uv run video-agent acceptance --no-media
uv run video-agent acceptance --project-id <PROJECT_ID>
uv run video-agent acceptance --project-id <PROJECT_ID> --report data/acceptance-report.json
```

`--no-media` is readiness-only. A full acceptance run must execute actual local model inference on the target M4. CI intentionally does not download model weights.

## Phase 14 — Semantic / visual evaluation

**In progress.** `app/evaluation.py` adds a deterministic baseline that scores project-prompt lexical alignment and adjacent-scene lexical continuity. It first requires hard deterministic QA to pass and writes a separate `evaluation-report.json` so evaluation can never override integrity QA.

The baseline is deliberately not represented as visual understanding. Remaining work is local image/scene semantic evaluation, I2V motion quality, narration/script alignment, stronger storyboard-to-media consistency, visual continuity, final-video evaluation, and an optional local-model evaluator behind a provider boundary.

## Phase 17 — Security/locality hardening

**In progress.** Renderer artifact resolution rejects absolute/relative paths that resolve outside the project directory. Planning-job paths use storage-root containment, and stale `queued`/`running` planning jobs become `interrupted` after restart. HTTP prompt/style/duration inputs have bounded sizes.

Remaining work includes the complete filesystem/symlink audit, prompt/manifest validation, subprocess audit, loopback verification, local-only inference review, secret/config handling, malformed artifact tests, dependency/security scanning, and explicit threat-model documentation.

## Phase 18 — Testing and CI/CD

Tests now include acceptance readiness/report contracts, planning restart recovery, deterministic semantic evaluation, and the existing provider/media/QA/API/job coverage. Continue expanding provider contract, failure-injection, security, migration, and deterministic end-to-end tests. Hardware acceptance remains intentionally outside standard model-free CI.

## Phases 15–16

Use real failure data for advanced bounded recovery/refinement and formalize provider/model profiles, compatibility, readiness, hardware-class selection, and deterministic fallback graphs.

## Phases 19–22

Complete observability, persistence/schema migrations, M4 performance optimization based on real measurements, and the V1 production gate. V1 requires the full local workflow from brief through validated final MP4, dashboard playback, restart/resume, reproducibility, and target-machine acceptance.

## Phases 23–24

After V1 stability, consider richer production editing/features and longer-term runtime/platform evolution while preserving local-first privacy/resource boundaries.

## Current execution order

```text
13 acceptance harness  [IMPLEMENTED]
        ↓
real M4 model/media acceptance  [TARGET MACHINE]
        ↓
14 semantic/visual evaluation  [IN PROGRESS]
        ↓
15 advanced recovery
        ↓
16 provider/model registry
        ↓
17 security hardening  [IN PROGRESS]
        ↓
18 test/CI expansion
        ↓
19 observability
        ↓
20 schema evolution
        ↓
21 M4 optimization
        ↓
22 V1 production gate
        ↓
23–24 V2/V3
```

## Immediate machine blocker

The target-M4 runtime previously failed because the configured SDXL directory was empty. The application correctly failed locally rather than downloading remotely. Once the Hugging Face SDXL download completes, run the Phase 13 full acceptance command against a storyboard-ready project.

The repository must never claim the hardware gate passed from CI alone. Real model loading, generation, memory pressure, thermal behavior and output quality require the actual M4 machine.

## Definition of done

Every phase requires implementation, deterministic tests where applicable, documentation, CI validation, explicit acceptance criteria, and target-machine validation whenever behavior depends on real hardware/model execution.

`plan.md` is the source of truth and must be updated after meaningful implementation commits.
