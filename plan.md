# Local AI Video Generator — Detailed Engineering Plan

## 1. Vision

Build a local-first AI video production system for Apple Silicon that accepts a natural-language idea and turns it into a finished video through a reproducible, inspectable pipeline.

Example:

```bash
video-agent create "Create a 60-second cinematic video explaining how AI agents work" \
  --duration 60 \
  --style cinematic \
  --aspect-ratio 16:9
```

The system progressively automates requirements extraction, creative brief, script, storyboard, visual prompts, local image/video generation, local TTS, subtitles, music/ambience, timeline assembly, quality validation, rendering, and project archiving.

The local LLM is the **director/orchestrator**. Specialized models and deterministic software generate and validate media. LLM output is never treated as executable code.

---

# 2. Target Hardware and Runtime

Primary target:

- Apple M4
- 36 GB unified memory
- macOS / Apple Silicon
- Metal-compatible acceleration where supported
- Local-first inference
- No paid cloud inference required for the core pipeline

The application is resource-aware. It must not assume that arbitrary large video models fit in 36 GB unified memory.

### Resource policy

Track:

- total/available memory where measurable
- disk space
- loaded providers/models
- generation concurrency
- operation duration
- output sizes

Default heavyweight media concurrency: **1** until real measurements justify more.

### Quality profiles

- **Fast:** fastest practical models/settings, lower media resolution, minimal post-processing.
- **Balanced:** default practical quality/performance.
- **Quality:** highest locally practical settings with longer execution time.

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
                         USER
                           │
                           ▼
                  ┌────────────────┐
                  │ CLI / Web UI   │
                  └───────┬────────┘
                          │
                          ▼
                  ┌────────────────┐
                  │ Project API    │
                  └───────┬────────┘
                          │
                          ▼
                  ┌────────────────┐
                  │ Orchestrator   │
                  └───────┬────────┘
                          │
                          ▼
                  ┌────────────────┐
                  │ Local Director │
                  │ Ollama/Qwen/   │
                  │ Llama          │
                  └───────┬────────┘
                          │
                    project plan
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
      Image           Video              TTS
      Provider        Provider          Provider
          │               │                │
          └───────────────┼────────────────┘
                          ▼
                  ┌────────────────┐
                  │ QA / Validation │
                  └───────┬────────┘
                          ▼
                  ┌────────────────┐
                  │ FFmpeg Render  │
                  └───────┬────────┘
                          ▼
                       final.mp4
```

The key boundary is:

> **LLM decides and coordinates; deterministic application code validates, executes, stores, and renders.**

---

# 5. Repository Development System

This repository must be developed using the rules in:

- `AGENTS.md` — AI-agent engineering policy.
- `docs/AGENTS_AND_SKILLS.md` — agent roles and skill-selection rules.
- `.agents/skills/` — focused reusable skills.
- `CONTRIBUTING.md` — development workflow and coding standards.
- `TESTING.md` — complete test strategy.
- `docs/DOCUMENTATION_STANDARD.md` — documentation Definition of Done.

Agents must load the smallest applicable set of skills for each task. Core implementation changes normally require coding + testing. Provider changes also require provider-integration + performance. File/process changes require security. Major architecture changes require architecture/review. Every meaningful change must update the relevant documentation.

---

# 6. Agent Roles

### Architect Agent

Owns architecture boundaries, interfaces, data models, dependency direction, and major design decisions.

### Director/Prompt Agent

Owns creative brief, script, storyboard, prompt templates, and structured generation instructions.

### Implementation Agent

Implements focused features with tests and documentation.

### Provider Agent

Integrates and validates local LLM/image/video/TTS/music backends behind adapters.

### QA/Test Agent

Builds unit, contract, integration, regression, and end-to-end tests.

### Performance Agent

Measures speed/memory/disk/concurrency on the target M4 and protects safe defaults.

### Security Agent

Reviews filesystem, subprocess, model-output, configuration, and dependency risks.

### Documentation Agent

Maintains architecture docs, setup/configuration docs, CLI/API docs, troubleshooting, examples, ADRs, migration notes, and phase status. Documentation is part of Definition of Done.

### Reviewer Agent

Performs final correctness, security, test, architecture, resource, and documentation review.

---

# 7. Core Components

## 7.1 CLI

Target commands:

```bash
video-agent doctor
video-agent health
video-agent create "topic" --duration 60
video-agent inspect <project-id>
video-agent plan <project-id>
video-agent generate <project-id>
video-agent generate-scene <project-id> <scene-id>
video-agent render <project-id>
video-agent resume <project-id>
video-agent clean <project-id>
video-agent cache stats
video-agent cache clear
```

## 7.2 Project Manager

State machine:

```text
CREATED
BRIEF_READY
SCRIPT_READY
STORYBOARD_READY
ASSETS_GENERATING
ASSETS_READY
AUDIO_READY
READY_TO_RENDER
RENDERING
COMPLETED
FAILED
CANCELLED
```

## 7.3 Director

Converts user intent into validated production instructions.

Responsibilities:

- requirements extraction
- creative brief
- script
- storyboard
- scene visual prompts
- motion prompts
- continuity metadata
- preferred/fallback media strategy

## 7.4 Orchestrator

Responsibilities:

- execute stages
- call providers
- validate outputs
- store artifacts
- retry only safe failures
- resume partial projects
- route scenes to providers
- enforce resource policy

## 7.5 Provider Registry

Provider implementations are registered by capability and configuration rather than referenced directly by business logic.

---

# 8. Canonical Data Model

Use typed Pydantic models at application boundaries.

## VideoProject

```text
schema_version
id
created_at
updated_at
source_prompt
title
language
target_audience
tone
duration_seconds
aspect_ratio
resolution
fps
style
quality_profile
voice_profile
music_profile
scenes
provider_plan
status
metadata
```

## Scene

```text
id
index
start_time
duration
narration
visual_description
image_prompt
motion_prompt
negative_prompt
camera
composition
lighting
style
characters
subjects
reference_assets
preferred_media_type
fallback_media_type
image_asset
video_asset
audio_asset
subtitle_range
validation
status
metadata
```

## Artifact

```text
id
project_id
scene_id
artifact_type
path
mime_type
provider
model
model_version
sha256
created_at
parameters
input_artifacts
status
```

## GenerationRun

```text
run_id
project_id
scene_id
stage
provider
model
input
parameters
started_at
completed_at
status
error
output_artifacts
```

---

# 9. Directory Layout

```text
local-ai-video/
├── plan.md
├── AGENTS.md
├── CONTRIBUTING.md
├── TESTING.md
├── README.md
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
├── Makefile
│
├── .agents/
│   └── skills/
│       ├── coding/SKILL.md
│       ├── testing/SKILL.md
│       ├── provider-integration/SKILL.md
│       ├── security/SKILL.md
│       ├── performance/SKILL.md
│       ├── debugging/SKILL.md
│       ├── review/SKILL.md
│       └── documentation/SKILL.md
│
├── app/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── logging.py
│   ├── exceptions.py
│   ├── health.py
│   ├── preflight.py
│   ├── models/
│   ├── director/
│   ├── orchestrator/
│   ├── providers/
│   ├── render/
│   ├── storage/
│   └── api/
│
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

Generated media/model weights/cache must remain excluded from Git.

---

# 10. Phase 0 — Foundation and Environment

## Objective

Create a clean control plane for the local pipeline.

## Completed implementation

- Python package foundation.
- `uv` dependency configuration.
- Ruff, Pytest, and mypy configuration.
- Pydantic configuration models.
- Typer CLI.
- Structured correlation logging.
- YAML configuration example/loading.
- Domain-specific exceptions.
- Filesystem project store with path containment checks.
- Disk-capacity preflight.
- Memory and disk resource snapshot.
- Apple Silicon detection.
- Python runtime detection.
- FFmpeg detection.
- Ollama local health/model detection.
- `video-agent health`.
- `video-agent doctor`.
- Unit tests for configuration, health, Ollama adapter, and filesystem behavior.
- Git ignore rules for generated media/model/cache artifacts.
- Makefile quality commands.
- GitHub Actions quality gates for formatting, lint, type checking, and tests.
- Documentation standard and agent documentation requirements.

## Phase 0 acceptance

Local validation command:

```bash
make check
make doctor
```

The repository-side foundation is complete. Final hardware acceptance must be executed on the user's M4 Mac because GitHub CI cannot validate the actual local Ollama/FFmpeg installation and Apple Silicon resource behavior.

**Status: CODE COMPLETE — LOCAL M4 ACCEPTANCE PENDING**

---

# 11. Phase 1 — Local LLM Director

## Objective

Use the local LLM as the creative director while keeping all model output strictly validated.

## Implemented so far

- Local `LLMProvider` protocol.
- Typed `LLMRequest` and `LLMResponse` structures.
- Ollama `/api/chat` generation adapter.
- Localhost-only enforcement in the Ollama adapter.
- Structured response metadata capture.
- Validated `CreativeBrief` Pydantic schema.
- Director system prompt with local-only and non-executable-output constraints.
- Director brief generation and JSON validation.
- Unit tests for valid and invalid Director output.

## Remaining

- real M4 Ollama inference acceptance
- JSON repair/retry policy
- full `VideoProject` creation from the brief
- script generation
- storyboard generation
- prompt versioning files

**Status: IN PROGRESS**

---

# 12. Phase 2 — Script and Storyboard

## Script

Must respect duration, audience, language, tone, and structure.

## Storyboard

Each scene must contain:

- timing
- narration
- visual objective
- image prompt
- motion prompt
- camera/framing
- lighting
- continuity references
- preferred/fallback strategy

## Validation

- duration > 0
- no negative scene duration
- no overlapping intervals
- scene total approximately equals project duration
- narration compatible with scene duration
- required prompts present

---

# 13. Phase 3 — Local Image Generation

Implement:

```python
class ImageProvider(Protocol):
    def generate(self, request: ImageGenerationRequest) -> ImageResult: ...
```

Persist prompt, negative prompt, seed, model, provider, parameters, and output hash.

Start with a practical local backend on Apple Silicon. Keep the interface compatible with ComfyUI or another local runtime as needed.

Acceptance: every scene can independently generate and validate an image asset.

---

# 14. Phase 4 — Local TTS

Implement:

```python
class TTSProvider(Protocol):
    def synthesize(self, request: TTSRequest) -> AudioResult: ...
```

Tasks:

- local voice registry
- per-scene synthesis
- duration measurement
- sample-rate normalization
- volume/loudness normalization
- concatenation
- metadata persistence

Acceptance: complete local narration track plus timing data.

---

# 15. Phase 5 — Subtitles and Timeline

Build a deterministic timeline data structure containing scenes, media assets, durations, audio, subtitle ranges, transitions, motion effects, and output settings.

Generate SRT and optionally WebVTT.

Do not embed hard-coded one-off FFmpeg commands throughout business logic.

---

# 16. Phase 6 — FFmpeg Rendering

Initial output:

- MP4
- H.264 video
- standard audio codec
- configurable FPS/resolution

Post-render validation:

- file exists
- file decodes
- video stream exists
- audio stream exists when expected
- duration within tolerance
- resolution/FPS correct

Acceptance: 30–60 second still-image + narration projects render end-to-end locally.

---

# 17. Phase 7 — AI Image-to-Video / Text-to-Video

Start with image-to-video because storyboard images already anchor composition and continuity.

Implement:

```python
class VideoProvider(Protocol):
    def generate(self, request: VideoGenerationRequest) -> VideoResult: ...
```

Tasks:

- evaluate Apple-Silicon-compatible local runtimes/models
- start with short clips
- capability metadata
- image-to-video provider
- clip validation
- static-motion fallback
- caching

Acceptance: one project can mix generated video clips, animated stills, and narration into one final MP4.

---

# 18. Phase 8 — Scene-Level Media Strategy

Each scene supports:

```text
STATIC_IMAGE
IMAGE_MOTION
IMAGE_TO_VIDEO
TEXT_TO_VIDEO
```

Selection considers:

- scene importance
- requested duration
- quality profile
- provider capability
- available memory
- generation time
- continuity

Use deterministic rules first. LLM-assisted routing can come later within strict policy bounds.

---

# 19. Phase 9 — Quality Assurance

### Image

- integrity
- dimensions
- aspect ratio
- blank/invalid output detection where practical

### Video

- decode
- duration
- resolution
- stream validation

### Audio

- decode
- duration
- loudness/silence checks where practical

### Project

- all required assets exist
- timeline valid
- subtitle timing valid
- final duration valid

The pipeline must identify the exact failed artifact/scene and make targeted regeneration possible.

---

# 20. Phase 10 — Agentic Recovery and Refinement

Bounded autonomy only.

Example retry budgets:

```text
LLM structured-output repairs: 2
image generation retries: 2
video generation retries: 2
render retries: 1
```

Examples:

- narration too long → rewrite narration → re-run TTS
- image provider fails → simplify prompt → retry → fallback
- video memory risk → reduce resolution/clip length → fallback to image motion

No infinite loops.

---

# 21. Phase 11 — Web API and UI

FastAPI target endpoints:

```text
POST /projects
GET /projects/{id}
POST /projects/{id}/plan
POST /projects/{id}/generate
POST /projects/{id}/scenes/{scene}/generate
POST /projects/{id}/render
POST /projects/{id}/resume
GET /projects/{id}/artifacts
GET /projects/{id}/events
GET /health
GET /providers
```

Local UI should initially expose:

- prompt
- duration
- aspect ratio
- style
- language
- voice
- quality
- scene preview
- regenerate scene
- render
- final video preview

---

# 22. Phase 12 — Persistence and Resume

Start with filesystem + JSON manifests. Introduce SQLite only when project/job count requires indexed querying.

On restart:

1. Load manifest.
2. Validate existing artifacts.
3. Verify hashes where enabled.
4. Mark missing/corrupt outputs incomplete.
5. Resume from first incomplete stage.

---

# 23. Phase 13 — Caching

Cache key includes:

```text
provider
model
model_version
normalized_prompt
negative_prompt
parameters
seed
input_artifact_hashes
```

Changed generation settings must invalidate old cache entries.

---

# 24. Phase 14 — Provider/Model Registry

Provider records should include capability and resource metadata.

Example:

```text
provider: local-video
image_to_video: true
text_to_video: false
max_duration: 5
preferred_resolution: ...
memory_class: high
```

This metadata is consumed by deterministic routing logic.

---

# 25. Phase 15 — Evaluation Framework

Maintain fixed benchmark prompts for:

- educational explainer
- product advertisement
- cinematic scene
- social short
- technical tutorial
- storytelling
- character continuity

Track:

- planning validity
- generation success rate
- render success rate
- generation latency
- memory failures
- regeneration rate
- cache hit rate
- duration accuracy

Human evaluation can later rate visual relevance, prompt adherence, narrative quality, audio quality, and temporal consistency.

---

# 26. Phase 16 — Security and Safety

Apply repository security skill to any filesystem/process/provider change.

Required:

- no shell interpolation
- path traversal prevention
- bounded subprocesses
- sanitized filenames
- secret-safe logging
- media validation
- dependency/license awareness
- no arbitrary code execution from LLM output

---

# 27. Phase 17 — Testing and CI

## CI must run

1. Formatting check
2. Lint
3. Type checks where configured
4. Unit tests
5. Contract tests
6. Lightweight integration tests

## Separate hardware suite

Actual model/runtime tests may be marked:

```text
hardware
models
slow
```

and executed on the actual Apple Silicon environment.

## Minimum critical test matrix

- valid/invalid project schema
- scene timing
- invalid LLM JSON
- prompt validation
- provider failure
- retry limits
- cache invalidation
- corrupt media
- render plan
- FFmpeg failure
- duration validation
- path traversal
- subprocess timeout
- resume behavior

See `TESTING.md` for complete cases.

---

# 28. Phase 18 — Observability

Each operation gets a correlation context:

```text
project_id
run_id
scene_id
stage
provider
model
```

Logs should allow an engineer to determine what failed, where, with which provider/model, how long it took, and which artifact was produced.

Do not log secrets or unnecessary sensitive content.

---

# 29. Phase 19 — Performance Engineering

Measure before optimization.

Baseline:

- LLM latency
- image generation latency
- video generation latency
- TTS latency
- FFmpeg render latency
- peak memory where measurable
- output size

Protect the M4/36 GB target with preflight checks and conservative media concurrency.

---

# 30. Definition of V1

This command must work:

```bash
video-agent create "Create a 60-second educational video explaining AI agents" \
  --duration 60 \
  --style cinematic
```

Expected output:

```text
data/projects/<project-id>/
├── project.json
├── brief.json
├── script.json
├── storyboard.json
├── scenes/
│   ├── scene-01/
│   │   ├── scene.json
│   │   ├── image.png
│   │   └── generation.json
│   └── ...
├── audio/
│   ├── scene-01.wav
│   └── narration.wav
├── subtitles/
│   └── subtitles.srt
├── render/
│   ├── render-plan.json
│   └── final.mp4
└── manifest.json
```

V1 must:

- run locally
- not require paid cloud inference
- regenerate one scene
- resume failed work
- validate final MP4
- persist generation metadata

---

# 31. Definition of V2 — AI Motion

Adds:

- local image-to-video provider
- scene-level media strategy
- video quality checks
- static fallback
- capability registry
- caching

---

# 32. Definition of V3 — Video Agent

Adds:

- automatic provider routing
- quality evaluation
- bounded repair loops
- prompt refinement
- narration correction
- local web UI
- project history

---

# 33. Engineering Best Practices

1. Keep provider integrations isolated.
2. Keep business logic independent of concrete model names.
3. Persist expensive generation metadata.
4. Validate model/provider output at every boundary.
5. Prefer deterministic logic over unnecessary LLM calls.
6. Keep retries bounded.
7. Make every stage independently rerunnable.
8. Do not commit generated binaries.
9. Do not commit secrets.
10. Avoid unrelated refactors.
11. Use regression tests for deterministic bugs.
12. Measure on actual target hardware before optimizing.
13. Document architecture-impacting decisions.
14. Treat prompt files as versioned source code.
15. Keep schemas versioned and migrate old projects explicitly.
16. Use typed/domain-specific errors.
17. Fail clearly rather than silently falling back.
18. Prefer one complete vertical slice over many incomplete abstractions.
19. Documentation updates are part of the same change as the feature they describe.

---

# 34. First Vertical Slice

The first implementation target is intentionally narrow:

```text
user prompt
  ↓
Ollama
  ↓
validated project
  ↓
validated storyboard
  ↓
3 deterministic test images
  ↓
local TTS
  ↓
subtitles
  ↓
FFmpeg
  ↓
final.mp4
```

Only after this works reliably should advanced image/video generation be introduced.

---

# 35. Exact Initial Implementation Sequence

1. Python project foundation
2. `uv` environment
3. config loader
4. structured logging
5. health/doctor
6. Pydantic project model
7. Pydantic scene model
8. artifact model
9. filesystem project store
10. Ollama adapter
11. Director prompt
12. brief generation
13. script generation
14. storyboard generation
15. storyboard validation
16. image provider interface
17. first local image backend
18. image asset validation
19. TTS provider interface
20. first local TTS backend
21. subtitle generation
22. timeline builder
23. FFmpeg render plan
24. FFmpeg renderer
25. final video validation
26. end-to-end CLI
27. resume support
28. per-scene regeneration
29. cache
30. video provider interface
31. local image-to-video backend
32. scene-level routing
33. quality evaluator
34. bounded repair engine
35. FastAPI
36. local UI
37. SQLite/job history if justified
38. benchmark suite
39. hardware performance tuning

---

# 36. First Coding Session Checklist

Implemented during Phase 0:

- [x] `pyproject.toml`
- [x] package structure
- [x] config loader
- [x] logging
- [x] `video-agent health`
- [x] `video-agent doctor`
- [x] initial Pydantic project model
- [x] filesystem store
- [x] Ollama health check
- [x] FFmpeg health check
- [x] memory/disk preflight
- [x] unit tests
- [x] CI quality gates
- [x] documentation standard

Phase 1 progress:

- [x] LLM provider contract
- [x] Ollama chat generation adapter
- [x] localhost-only provider enforcement
- [x] CreativeBrief schema
- [x] Director brief generation
- [x] Director structured-output tests
- [ ] JSON repair/retry
- [ ] real M4 inference acceptance
- [ ] full project creation
- [ ] script generation
- [ ] storyboard generation

---

# 37. Non-Goals for Early Development

Do not initially build:

- multi-user SaaS authentication
- Kubernetes/distributed inference
- GPU cluster orchestration
- custom model training
- custom codecs
- complex microservices
- cloud-only core path
- unrestricted autonomous agents

---

# 38. Project Success Criteria

Success means a user can remain on the M4 Mac, enter a natural-language video request, and receive a reproducible MP4 without manually assembling scripts, images, audio, subtitles, and editing steps.

An engineer must be able to inspect every intermediate artifact, replace one provider/model, rerun a single scene, resume an interrupted project, and reproduce a final render from a saved manifest.

---

# 39. Implementation Log

The plan is updated as implementation progresses. Each meaningful implementation commit must update this section and the relevant phase status. Where GitHub's file-content API requires separate commits for individual files, the next plan synchronization commit records all intervening changes.

### Phase 0 implementation log

- Added Python project/dependency/tooling foundation.
- Added local-only configuration and YAML example.
- Added structured logging and domain exceptions.
- Added filesystem project storage and disk preflight.
- Added memory/disk resource snapshot.
- Added Ollama local health/model detection.
- Added health/doctor CLI checks.
- Added tests and GitHub Actions quality gates.
- Added documentation Definition of Done and strengthened AI-agent operating rules.

**Status:** CODE COMPLETE — LOCAL M4 ACCEPTANCE PENDING.

### Phase 1 implementation log

- Added typed local LLM provider contract.
- Implemented Ollama `/api/chat` generation.
- Enforced localhost-only Ollama endpoints.
- Added validated CreativeBrief schema.
- Added Director brief generation with JSON/Pydantic validation.
- Added Director tests for valid and malformed model output.

**Status:** IN PROGRESS — real M4 inference and remaining Director pipeline stages pending.

### Latest implementation synchronization

This plan update records the Phase 1 implementation currently present in the repository. Future meaningful implementation commits must keep this log and the relevant checklist synchronized.

**Next:** complete Phase 1 structured-output repair, project creation, script, and storyboard pipeline.
