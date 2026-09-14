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
| 18 | Testing pyramid + CI/CD expansion | PARTIALLY IMPLEMENTED; acceptance/restart regression tests added |
| 19 | Observability/operational diagnostics | PARTIALLY IMPLEMENTED |
| 20 | Persistence/schema migrations | PLANNED |
| 21 | M4 resource/performance optimization | PLANNED; depends on measurements |
| 22 | V1 production gate | PLANNED |
| 23 | V2 advanced production features | FUTURE |
| 24 | V3 platform evolution/research | FUTURE |

## Implemented foundation: Phases 0–13

The repository contains the validated local Director pipeline, typed domain contracts, local Ollama integration, Diffusers image generation, macOS Speech narration, deterministic timelines/subtitles, FFmpeg rendering, LTX image-to-video integration, deterministic media routing/fallback, content-addressed scene-video caching, deterministic QA, bounded recovery, loopback web UI/API, persistent JSON-backed planning/media jobs, progress reporting, restart recovery, final-video gating, target-machine acceptance reporting, renderer path containment, and stale planning-job recovery.

The job layer owns scheduling/lifecycle only. Director, media generation, provider, recovery, QA, artifact persistence and rendering remain the authoritative boundaries.

## Phase 13 — Target-machine acceptance harness

**Implemented in main.**

`app/acceptance.py` provides local-only/platform/tool/model readiness checks, MPS readiness, model-load timing, real scene image generation timing, real configured video-provider model-load timing when applicable, real scene-video generation timing, before/after resource snapshots, deterministic project QA, final FFmpeg render/final QA, and a machine-readable JSON report.

```bash
uv run video-agent acceptance --no-media
uv run video-agent acceptance --project-id <PROJECT_ID>
uv run video-agent acceptance --project-id <PROJECT_ID> --report data/acceptance-report.json
```

`--no-media` is readiness-only. A full acceptance run must execute actual local model inference on the target M4. CI intentionally does not download model weights.

## Phase 14 — Semantic / visual evaluation

**In progress.** A deterministic baseline now scores project-prompt lexical alignment and adjacent-scene lexical continuity while refusing to run when deterministic hard QA fails. Reports are persisted separately as `evaluation-report.json` so evaluation cannot override integrity QA.

Remaining work:

- local image/scene semantic evaluation;
- I2V motion quality evaluation;
- narration/script alignment;
- stronger storyboard-to-media consistency;
- visual continuity beyond lexical overlap;
- final-video evaluation protocol;
- optional local-model evaluator behind a provider boundary.

No semantic score may override a hard media-integrity failure.

## Phase 15 — Advanced recovery/refinement

Use real failure data to add structured failure classification, resource-aware prompt/settings refinement, selective regeneration, dependency-aware invalidation, per-job/project recovery budgets, and persistent recovery history. No infinite retries or uncontrolled policy escalation.

## Phase 16 — Provider/model registry

Centralize provider/model profiles, compatibility checks, health/readiness contracts, hardware-class selection, deterministic fallback graphs, provider-specific configuration isolation, and compatibility tests.

## Phase 17 — Security/locality hardening

**In progress.** Renderer artifact resolution rejects absolute/relative paths that resolve outside the project directory. Planning-job paths use storage-root containment and stale `queued`/`running` jobs become `interrupted` after restart. HTTP prompt/style/duration inputs now have bounded sizes.

Remaining work includes complete filesystem/symlink audit, prompt/manifest validation, subprocess audit, loopback verification, local-only inference review, secret/config handling, malformed artifact tests, dependency/security scanning, and explicit threat-model documentation.

Security invariant: malformed input must never become arbitrary filesystem access, subprocess execution, remote upload, or uncontrolled resource consumption.

## Phase 18 — Testing and CI/CD

Current tests cover deterministic application boundaries plus acceptance-readiness and planning restart recovery. Continue expanding provider contract tests, failure-injection tests, security regression tests, migration tests, and deterministic end-to-end coverage. Hardware acceptance remains intentionally outside standard model-free CI.

Required regressions include retry exhaustion, malformed LLM output, stale artifacts/briefs, timeline errors, hash mismatch, unavailable providers, memory gates, cache boundaries, restart recovery, traversal attacks, invalid API transitions, and invalid final MP4s.

## Phase 19 — Observability

Complete structured lifecycle events, stage/job/project correlation, generation timing, provider/model/device metadata, resource snapshots, failure classification, acceptance aggregation, privacy-preserving diagnostics, and log retention/rotation.

## Phase 20 — Persistence evolution

Add explicit schema versions and migrations, compatibility readers, corruption detection, migration tests, pre-migration snapshots, and project/job/artifact compatibility rules. Keep the filesystem unless measurements prove a database is required.

## Phase 21 — M4 optimization

Use real acceptance measurements to tune cold/warm model load, unified-memory peak/steady state, CPU/MPS utilization, disk I/O, thermal behavior, resolution/steps/FPS profiles, concurrency, cache effectiveness, memory cleanup, and long-running stability.

Optimize for reliable local production rather than theoretical model size.

## Phase 22 — V1 production gate

V1 requires the complete local workflow: brief → storyboard → scene media → bounded recovery → deterministic QA → final MP4 → dashboard playback → restart/resume → reproducible persisted project. V1 is not complete until target M4/model/resource acceptance and representative end-to-end projects pass.

## Phases 23–24

After V1 stability, consider richer transitions/camera controls/subtitles/audio layers/editing/templates/batch workflows, then longer-term multi-model orchestration, pluggable runtimes, richer interchange/evaluation, and optional indexing/database evolution. These must preserve the local-first architecture.

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
