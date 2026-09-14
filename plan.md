# Local AI Video Generator — Detailed Engineering Plan

## Current implementation checkpoint

Phase 0–8 are substantially implemented. Phase 9 deterministic quality assurance is implemented, including project QA reporting, targeted scene regeneration, media integrity validation, timeline/subtitle validation, and final-video validation. The next implementation milestone is Phase 10 bounded agentic recovery and refinement. Target Apple M4 / 36 GB hardware acceptance remains a separate machine-level acceptance activity.

The detailed phased plan below is the source of truth and must stay synchronized with meaningful repository commits.

---

# 1. Vision

Build a local-first AI video production system for Apple Silicon that accepts a natural-language idea and turns it into a finished video through a reproducible, inspectable pipeline.

The local LLM is the director/orchestrator. Specialized models and deterministic software generate and validate media. LLM output is never treated as executable code.

---

# 2. Target Hardware and Runtime

Primary target: Apple M4, 36 GB unified memory, macOS/Apple Silicon, Metal-compatible acceleration where supported, local-first inference, and no paid cloud inference required for the core pipeline.

Resource policy:
- track total/available memory and disk where measurable
- track provider/model and generation duration
- heavyweight media concurrency defaults to 1 until measured
- Fast, Balanced, and Quality profiles remain supported
- high-memory video routing is gated by host resource availability

---

# 3. Product Principles

1. Local-first.
2. Provider-agnostic.
3. Artifact-first.
4. Resumable.
5. Reproducible.
6. Observable.
7. Deterministic application logic around model calls.
8. Bounded agent autonomy.
9. Simple before sophisticated.
10. Measure before optimizing.
11. Never hide a provider or render failure behind fake success.

---

# 4. System Architecture

```text
USER → CLI/UI → Project API → Orchestrator → Local Director
                                      ↓
                           Image / Video / TTS providers
                                      ↓
                                  QA / Validation
                                      ↓
                                FFmpeg Render
                                      ↓
                                  final.mp4
```

Key boundary: **LLM decides and coordinates; deterministic application code validates, executes, stores, and renders.**

---

# 5. Repository Development System

The repository development contract is defined by `AGENTS.md`, `CONTRIBUTING.md`, `TESTING.md`, `.agents/skills/`, and `docs/DOCUMENTATION_STANDARD.md`. Documentation is part of Definition of Done. Generated media/model weights/cache remain excluded from Git.

---

# 6. Core Components

## CLI

Implemented commands include `doctor`, `health`, `create`, `resume`, `generate-scene`, `generate-audio`, `generate-video`, `generate-media`, `subtitles`, `timeline`, `qa`, `regenerate-scene`, and `render`.

Planned: cache statistics/cleanup, inspect, and broader end-to-end generation.

## Orchestrator

Executes stages, calls providers, validates outputs, stores artifacts, resumes partial work, routes scenes, and enforces resource policy.

## Provider Registry

Video capabilities are centralized in a deterministic registry. Broader provider/model construction and version/resource metadata remain planned.

---

# 7. Canonical Data Model

Typed Pydantic models are used at application boundaries for projects, scenes, artifacts, timelines, and provider requests/results.

---

# 8. Directory Layout

```text
local-ai-video/
├── plan.md
├── AGENTS.md
├── CONTRIBUTING.md
├── TESTING.md
├── README.md
├── pyproject.toml
├── uv.lock
├── .agents/skills/
├── app/
├── prompts/
├── workflows/
├── docs/
├── scripts/
├── examples/
├── tests/
└── data/
    ├── projects/
    ├── cache/
    └── models/
```

---

# 9. Phase 0 — Foundation and Environment

**Status: CODE COMPLETE — LOCAL M4 ACCEPTANCE PENDING**

Implemented Python/uv foundation, configuration, CLI, structured logging, YAML configuration, domain exceptions, filesystem storage/path safety, disk and resource preflight, Apple Silicon/runtime/FFmpeg/Ollama health checks, Makefile quality commands, CI quality gates, tests, and documentation standards.

---

# 10. Phase 1 — Local LLM Director

**Status: CODE COMPLETE — LOCAL M4 ACCEPTANCE PENDING**

Implemented local Ollama provider, loopback-only endpoint enforcement, model preflight, validated creative brief/script/storyboard generation, bounded structured-output repair, prompt versioning, persistence, atomic artifacts, project status transitions, GenerationRun metadata, and Director resume behavior.

Remaining machine-level acceptance: real M4 Ollama inference and further schema/narration compatibility refinement.

---

# 11. Phase 2 — Script and Storyboard

**Status: IMPLEMENTED BASELINE**

Implemented scene timing/non-overlap and target-duration validation plus scene visual/motion/narration data used by downstream media generation. Further schema enrichment remains possible without weakening validation boundaries.

---

# 12. Phase 3 — Local Image Generation

**Status: IMPLEMENTED — HARDWARE ACCEPTANCE PENDING**

Implemented `ImageProvider`, local Diffusers image generation, MPS/CPU selection, local-files-only model loading, deterministic generation parameters, output hashing, persistence, and per-scene generation.

---

# 13. Phase 4 — Local TTS

**Status: IMPLEMENTED — HARDWARE ACCEPTANCE PENDING**

Implemented `TTSProvider`, macOS Speech `say`, per-scene synthesis, WAV metadata/duration capture, narration assembly, normalization, and persistence.

---

# 14. Phase 5 — Subtitles and Timeline

**Status: IMPLEMENTED**

Implemented deterministic SRT/WebVTT generation and canonical timeline building used by rendering and project QA.

---

# 15. Phase 6 — FFmpeg Rendering

**Status: IMPLEMENTED — HARDWARE ACCEPTANCE PENDING**

Implemented deterministic FFmpeg rendering, still-image/video scene handling, narration integration, silent fallback, H.264/AAC MP4 output, ffprobe validation, final artifact hashing, and render metadata.

---

# 16. Phase 7 — AI Image-to-Video / Text-to-Video

**Status: IMPLEMENTED BASELINE — HARDWARE ACCEPTANCE PENDING**

Implemented video provider contract, deterministic FFmpeg motion provider, local LTX image-to-video provider, capability metadata, scene-video persistence, deterministic cache keys, and scene-video QA before artifact acceptance.

LTX model loading, memory use, latency, and visual quality remain target-M4 acceptance work.

---

# 17. Phase 8 — Scene-Level Media Strategy

**Status: IMPLEMENTED BASELINE — HARDWARE ACCEPTANCE PENDING**

Implemented deterministic scene media selection, centralized video capability registry, host resource snapshots, memory-aware routing, image-to-video selection, deterministic motion fallback, project-level media orchestration, asset lifecycle transitions, deterministic scene-video cache keys, validated cache reuse, scene-video FFprobe/decode QA, and `generate-media` CLI integration.

The LLM does not execute routing decisions directly; application code enforces capabilities, duration limits, memory policy, and fallback rules.

Remaining hardening: provider construction centralization, stronger fallback guarantees, explicit cache statistics/cleanup, and broader lifecycle/resume hardening.

---

# 18. Phase 9 — Quality Assurance

**Status: IMPLEMENTED — DETERMINISTIC QA COMPLETE**

Phase 9 provides deterministic QA across media, scenes, timelines, subtitles, and final video.

### Image QA

- existence/non-empty validation
- PNG signature/IHDR validation
- positive dimensions
- optional expected dimensions
- SHA-256 measurement

### Audio QA

- existence/non-empty validation
- bounded FFprobe invocation
- valid JSON and audio stream validation
- positive duration
- expected-duration tolerance validation

### Video QA

- existence/non-empty validation
- FFprobe metadata validation
- video stream validation
- duration validation
- resolution/FPS validation
- complete FFmpeg decode validation

### Project QA

- project/scene/artifact manifest validation
- scene/artifact UUID consistency
- per-scene image/audio/video validation
- timeline project/duration/continuity validation
- scene coverage validation
- subtitle file validation
- final-video validation when output exists

### Reporting and targeted regeneration

```bash
video-agent qa <PROJECT_ID>
video-agent regenerate-scene <PROJECT_ID> <SCENE_ID> --stage image
video-agent regenerate-scene <PROJECT_ID> <SCENE_ID> --stage audio
video-agent regenerate-scene <PROJECT_ID> <SCENE_ID> --stage video
video-agent regenerate-scene <PROJECT_ID> <SCENE_ID> --stage all
```

QA reports persist as `qa-report.json` with schema version, pass/fail state, exact failure scope, and actionable message. Targeted regeneration invalidates affected downstream media/cache state and re-runs QA.

### Phase 9 acceptance

Deterministic QA and targeted regeneration are implemented. CI validates deterministic behavior. Real model performance and visual-quality acceptance remain dependent on the target M4 environment.

---

# 19. Phase 10 — Agentic Recovery and Refinement

Next major phase. Recovery remains bounded and deterministic around model calls.

Initial budgets:
```text
LLM structured-output repairs: 2
image generation retries: 2
video generation retries: 2
render retries: 1
```

Recovery examples include bounded narration rewrite → TTS → QA, image retry/prompt simplification → deterministic fallback, and video resource reduction → fallback. No infinite loops or autonomous policy changes.

---

# 20. Phase 11 — Web API and UI

FastAPI target endpoints cover projects, planning, generation, scene generation, rendering, resume, artifacts, events, health, and providers. The local UI should expose prompt, duration, aspect ratio, style, language, voice, quality, scene preview, regeneration, rendering, and final-video preview.

---

# 21. Phase 12 — Persistence and Resume

Filesystem + JSON remains current persistence. Full cross-stage artifact/hash verification and recovery orchestration remain planned beyond Director resume and Phase 9 targeted regeneration.

---

# 22. Phase 13 — Caching

Deterministic scene-video generation keys are implemented. Planned: explicit project cache statistics, cleanup, lifecycle rules, and broader retention/invalidation management.

---

# 23. Phase 14 — Provider/Model Registry

Centralized video capability metadata is implemented. Planned: broader provider/model registration, construction, version metadata, and resource profiles.

---

# 24. Phase 15 — Evaluation Framework

Maintain fixed benchmark prompts and track planning validity, generation success rate, render success rate, latency, memory failures, regeneration rate, cache hit rate, duration accuracy, and later human-rated visual/narrative/audio/temporal quality.

---

# 25. Phase 16 — Security and Safety

Required controls remain: no shell interpolation, path traversal prevention, bounded subprocesses, sanitized filenames, secret-safe logging, media validation, dependency/license awareness, and no arbitrary code execution from LLM output.

---

# 26. Phase 17 — Testing and CI

CI runs formatting, lint, type checking, unit tests, contract tests, and lightweight integration tests. Hardware/model/slow suites belong on the actual Apple Silicon environment.

---

# 27. Phase 18 — Observability

Each operation should expose correlation context: project_id, run_id, scene_id, stage, provider, and model. Logs must identify failures, duration, provider/model, and artifacts without leaking secrets.

---

# 28. Phase 19 — Performance Engineering

Measure LLM, image, video, TTS, and FFmpeg latency; memory; disk; output size; and concurrency on the M4 target. Protect the 36 GB unified-memory target with conservative defaults and resource-aware routing.

---

# 29. Definition of V1

V1 requires a complete local project workflow, scene regeneration, resume, final MP4 validation, and persisted generation metadata without paid cloud inference.

---

# 30. Definition of V2 — AI Motion

V2 adds local image-to-video, scene-level media strategy, video QA, static fallback, capability registry, and caching. The repository now contains the baseline implementation for these capabilities.

---

# 31. Definition of V3 — Video Agent

V3 adds automatic provider routing, quality evaluation, bounded repair loops, prompt refinement, narration correction, and local web UI. These map primarily to Phases 9–11 and later evaluation work.
