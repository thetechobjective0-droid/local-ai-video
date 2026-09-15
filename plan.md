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
| 15 | Advanced recovery/refinement | PLANNED |
| 16 | Provider/model registry evolution | PLANNED |
| 17 | Security/locality hardening | IN PROGRESS; renderer/job containment + restart recovery hardened |
| 18 | Testing pyramid + CI/CD expansion | PARTIALLY IMPLEMENTED; acceptance/restart/evaluation/preflight/media-job/UI-polling/structured-output/progress-UI tests added; CLI mypy compatibility, read-only CI workflow, schema-aware Director fixtures, video-QA-isolated media tests, Ruff-formatted polling fixtures, and media-job formatter normalization hardened |
| 19 | Observability/operational diagnostics | PARTIALLY IMPLEMENTED |
| 20 | Persistence/schema migrations | PLANNED |
| 21 | M4 resource/performance optimization | IN PROGRESS; memory-efficient ML inference controls and acceptance resource measurements added |
| 22 | V1 production gate | PLANNED |
| 23 | V2 advanced production features | FUTURE |
| 24 | V3 platform evolution/research | FUTURE |

## Current implementation state

Phases 0–13 are implemented. Phase 14 has a deterministic semantic baseline. Security and CI expansion remain active. The target Mac runtime now has macOS-safe memory probing, media-only jobs no longer initialize the Diffusers image provider when all scene images are already persisted, and the browser dashboard no longer creates a second media-job polling loop from inside each polling tick. Director structured generation now passes the exact Pydantic JSON Schema to Ollama for both initial generation and bounded repair attempts. The dashboard now has a visible operation loader, refreshes project/scene state when a media job reaches a terminal state, uses a dedicated final-video readiness endpoint, and shows determinate planning/media progress bars. Media progress reflects completed scenes; planning progress is intentionally state-based (queued 0%, running 60%, completed 100%) until the planning backend exposes stage counts. Successful background media jobs now continue through timeline generation, subtitles, deterministic FFmpeg rendering, and final QA so the workflow does not stop at `assets_ready`. Media jobs now also ensure every narrated scene has a real, non-silent macOS TTS artifact before rendering; existing silent/missing audio is regenerated, and the macOS TTS provider rejects an entirely silent PCM result immediately. The image extra now explicitly installs Accelerate so Diffusers can use its lower-memory loading path on the target machine. Diffusers image and LTX inference now use `torch.inference_mode()`, capability-gated attention/VAE slicing and VAE tiling, and explicit post-generation cache/reference cleanup to reduce peak and retained accelerator memory. FFmpeg and FFprobe subprocesses now receive a sanitized macOS environment without malloc stack-logging variables, removing the repeated `MallocStackLogging` diagnostics seen during finalization. CI regression fixtures now distinguish real provider identities, isolate orchestration tests from FFprobe while retaining FFprobe as the production video-quality gate, and remain Ruff-format compliant. The media-job orchestration module is normalized to the formatter version resolved by CI. Deterministic evaluation now also scores narration-to-visual lexical alignment and image-prompt-to-motion-prompt storyboard consistency, while remaining explicitly non-visual. Target-machine acceptance now records peak process RSS and process CPU seconds alongside wall-clock stage timings and before/after memory/disk snapshots.

The repository must never claim the hardware gate passed from CI alone. Real model loading, generation, memory pressure, thermal behavior and output quality require the actual M4 machine.

## Phase 13 — Target-machine acceptance harness

`app/acceptance.py` provides local-only/platform/tool/model readiness checks, MPS readiness, model-load timing, real scene image/video generation timing, before/after resource snapshots, deterministic project QA, final FFmpeg render/final QA, and a machine-readable JSON report. It now additionally records peak process RSS and process CPU seconds for evidence-driven performance analysis.

```bash
uv run video-agent acceptance --no-media
uv run video-agent acceptance --project-id <PROJECT_ID>
uv run video-agent acceptance --project-id <PROJECT_ID> --report data/acceptance-report.json
```

`--no-media` is readiness-only. Full acceptance executes actual local model inference on the target M4.

## Phase 14 — Semantic / visual evaluation

`app/evaluation.py` adds a deterministic baseline for project-prompt lexical alignment, adjacent-scene lexical continuity, visual-description-to-narration lexical alignment, and image-prompt-to-motion-prompt storyboard consistency. It requires hard deterministic QA to pass and writes `evaluation-report.json` separately from integrity QA. These metrics are lexical heuristics only and are not represented as visual understanding.

Remaining work is local image/scene semantic evaluation, I2V motion quality, stronger visual continuity, final-video evaluation, and an optional local-model evaluator behind a provider boundary.

## Phase 17 — Security/locality hardening

Renderer artifact resolution rejects paths outside the project directory. Planning-job paths use storage-root containment, stale `queued`/`running` jobs become `interrupted` after restart, HTTP prompt/style/duration inputs are bounded, and media subprocesses strip macOS malloc diagnostic variables before launching external tools.

Remaining work includes filesystem/symlink audit, prompt/manifest validation, subprocess audit, loopback verification, local-only inference review, secret/config handling, malformed artifact tests, dependency/security scanning, and threat-model documentation.

## Phase 18 — Testing and CI/CD

Tests cover deterministic application boundaries plus acceptance readiness/report contracts, planning restart recovery, semantic evaluation, macOS resource probing, demand-driven media-job image-provider initialization, browser dashboard polling regression, schema-constrained Director generation/repair, and dashboard progress UI. The dashboard regression prevents `pollJob()` from calling `refreshJobs()` on every tick, which previously multiplied polling loops and produced excessive repeated `/api/jobs` and `/api/projects/.../jobs` requests. Structured-output tests verify that the provider receives the exact Pydantic schema on both initial and repair calls. The strict mypy job is unblocked for the existing Typer `click_type` overload incompatibility in `app.cli`, and CI no longer writes formatting commits back to the repository or races with concurrent pushes. Director resume fixtures now select responses from the requested JSON schema, media orchestration tests mock only the FFprobe boundary so malformed fake bytes cannot mask production QA, the polling regression test is kept Ruff-format compliant, and the media-job module is aligned with the Ruff formatter actually resolved by CI. Continue expanding provider contract, failure-injection, security, migration, and deterministic end-to-end tests. Hardware acceptance remains outside standard model-free CI.

## Phase 21 — M4 resource/performance optimization

The ML providers now reduce inference memory pressure without changing model weights: attention slicing, VAE slicing, and VAE tiling are enabled only when supported by the loaded Diffusers pipeline; inference runs under `torch.inference_mode()`; temporary outputs are explicitly released; and Python/accelerator caches are collected after each generation. This is designed for the M4 / 36 GB unified-memory target while retaining the existing conservative single-media-job concurrency. Acceptance now measures peak process RSS and process CPU seconds in addition to stage wall-clock timings and before/after resource snapshots. These measurements provide a baseline for real-M4 optimization; CPU/GPU utilization, sustained thermal behavior, and model-specific latency still require target-machine runs and must not be inferred from CI.

## Phases 15–16, 19–20, 22–24

Use real failure data for advanced bounded recovery/refinement; formalize provider/model profiles; complete observability and schema evolution; then enforce the V1 production gate before V2/V3 expansion.

## Definition of done

Every phase requires implementation, deterministic tests where applicable, documentation, CI validation, explicit acceptance criteria, and target-machine validation whenever behavior depends on real hardware/model execution.

`plan.md` is the source of truth and must be updated after meaningful implementation commits.
