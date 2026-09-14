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

The system should progressively automate:

1. Requirements extraction
2. Creative brief
3. Script generation
4. Storyboard generation
5. Scene-level visual planning
6. Image prompt generation
7. Local image generation
8. Local video generation where appropriate
9. Local TTS narration
10. Subtitle generation
11. Music / ambience handling
12. Timeline assembly
13. Quality validation
14. Final rendering
15. Project archiving and reproducibility

The system is **not** intended to make Llama/Qwen generate video pixels. The local LLM is the director/orchestrator; specialized image, video, audio, and rendering components generate the media.

---

# 2. Target Hardware and Runtime

Primary target:

- Apple M4
- 36 GB unified memory
- macOS
- Apple Silicon / Metal-compatible inference where supported
- Local-first inference
- No paid cloud API required for the core pipeline

The application must be resource-aware. It must not assume that an arbitrary large video model will fit into 36 GB unified memory.

## 2.1 Resource policy

The runtime should track:

- Total system memory
- Available memory
- Current model/provider
- Estimated provider memory requirement
- Concurrent generation jobs
- CPU/GPU pressure where accessible
- Disk space for model and artifact storage

Initial policy:

- One heavyweight media generation job at a time.
- Small LLM tasks may run concurrently only after measurement.
- Video generation defaults to short clips.
- Failed or memory-heavy workflows should fall back to lower-quality profiles.

## 2.2 Quality profiles

Define three profiles:

### Fast

- Smaller/faster LLM
- Lower image resolution
- Short video clips
- Minimal post-processing
- Intended for development and iteration

### Balanced

- Preferred default
- Moderate image resolution
- Moderate generation settings
- Good TTS quality
- Basic enhancement

### Quality

- Highest practical local settings
- Longer generation time
- Higher image/video settings
- Additional validation/refinement

---

# 3. Product Principles

## 3.1 Local-first

Core workflow works without remote inference APIs.

## 3.2 Model-agnostic

Every model runtime is accessed through a provider interface. The application must not import a specific model implementation into business logic.

## 3.3 Artifact-first

Every major stage writes an artifact that can be inspected and reused.

Examples:

```text
brief.json
script.json
storyboard.json
scene-01.json
scene-01.png
scene-01.mp4
scene-01.wav
subtitles.srt
render.json
final.mp4
```

## 3.4 Resumable

A failed Stage N must not force Stages 1–N-1 to run again.

## 3.5 Reproducible

Persist:

- Model name
- Model version where available
- Prompt
- Negative prompt
- Seed
- Generation parameters
- Provider
- Software version
- Input artifact hashes
- Output artifact hashes

## 3.6 Observable

Every job should expose:

- Current stage
- Status
- Progress
- Error
- Start time
- End time
- Provider
- Artifacts generated

## 3.7 Incremental

Build a reliable still-image video generator first. Add AI motion only after the basic pipeline is reliable.

---

# 4. System Architecture

```text
                           USER
                            │
                            ▼
                    ┌───────────────┐
                    │ CLI / Web UI  │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Project API   │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Orchestrator  │
                    └───────┬───────┘
                            │
                ┌───────────┼───────────┐
                ▼           ▼           ▼
             Director    Validators   Scheduler
                │
                ▼
         ┌───────────────┐
         │ Local LLM     │
         │ Ollama        │
         │ Qwen/Llama    │
         └───────┬───────┘
                 │
             Project plan
                 │
      ┌──────────┼───────────┬─────────────┐
      ▼          ▼           ▼             ▼
   Image       Video        TTS          Music
 Provider    Provider    Provider      Provider
      │          │           │             │
      └──────────┴───────────┴─────────────┘
                         │
                         ▼
                 ┌───────────────┐
                 │ Render Engine │
                 │ FFmpeg        │
                 └───────┬───────┘
                         │
                         ▼
                      final.mp4
```

---

# 5. Core Components

## 5.1 CLI

Responsibilities:

- Create projects
- Inspect projects
- Generate stages
- Regenerate individual scenes
- Render video
- Resume failed jobs
- Check system health

Target commands:

```bash
video-agent health
video-agent create "topic" --duration 60
video-agent inspect <project-id>
video-agent generate <project-id>
video-agent generate-scene <project-id> <scene-id>
video-agent render <project-id>
video-agent resume <project-id>
video-agent clean <project-id>
```

## 5.2 Project manager

Creates and maintains project state.

Project states:

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

## 5.3 Director

The Director converts a user request into structured production instructions.

Responsibilities:

- Interpret requirements
- Identify missing information
- Select defaults
- Generate creative brief
- Generate script
- Generate storyboard
- Create visual prompts
- Create motion prompts
- Produce metadata for continuity

## 5.4 Orchestrator

The Orchestrator is deterministic application logic around the LLM, not an unconstrained autonomous loop.

Responsibilities:

- Execute stages
- Call providers
- Validate outputs
- Store artifacts
- Retry safe operations
- Resume incomplete work
- Route scenes to appropriate providers

## 5.5 Provider registry

Providers are discovered through a registry.

Example concept:

```python
registry.register("ollama", LLMProvider(...))
registry.register("local-image", ImageProvider(...))
registry.register("local-video", VideoProvider(...))
registry.register("local-tts", TTSProvider(...))
```

This allows backend replacement without changing the pipeline.

---

# 6. Canonical Data Model

Use typed Pydantic models for application boundaries.

## 6.1 VideoProject

```text
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
style
quality_profile
voice_profile
music_profile
scenes
status
provider_plan
metadata
```

## 6.2 Scene

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
status
validation
metadata
```

## 6.3 Artifact

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

## 6.4 GenerationRun

Persist every provider invocation:

```text
run_id
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

# 7. Directory Layout

```text
local-ai-video/
├── plan.md
├── README.md
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
├── Makefile
│
├── app/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── logging.py
│   ├── exceptions.py
│   ├── health.py
│   │
│   ├── models/
│   │   ├── project.py
│   │   ├── scene.py
│   │   ├── artifact.py
│   │   └── run.py
│   │
│   ├── director/
│   │   ├── director.py
│   │   ├── brief.py
│   │   ├── script.py
│   │   ├── storyboard.py
│   │   └── prompts.py
│   │
│   ├── orchestrator/
│   │   ├── engine.py
│   │   ├── state.py
│   │   ├── scheduler.py
│   │   └── recovery.py
│   │
│   ├── providers/
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── llm/
│   │   ├── image/
│   │   ├── video/
│   │   ├── tts/
│   │   └── music/
│   │
│   ├── render/
│   │   ├── ffmpeg.py
│   │   ├── timeline.py
│   │   ├── subtitles.py
│   │   ├── audio.py
│   │   └── validation.py
│   │
│   ├── storage/
│   │   ├── filesystem.py
│   │   ├── manifest.py
│   │   └── cache.py
│   │
│   └── api/
│       ├── app.py
│       ├── routes_projects.py
│       ├── routes_health.py
│       └── schemas.py
│
├── prompts/
│   ├── system/
│   ├── director/
│   ├── script/
│   ├── storyboard/
│   └── quality/
│
├── workflows/
│   ├── basic-image-video.yaml
│   ├── ai-motion-video.yaml
│   └── cinematic.yaml
│
├── scripts/
├── examples/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
└── data/
    ├── projects/
    ├── cache/
    └── models/
```

Generated media should never be committed to Git.

---

# 8. Phase 0 — Foundation and Environment

## Goal

Get a clean, testable Python foundation running on the M4 Mac.

## Tasks

1. Initialize Python package.
2. Choose `uv` for environment/dependency management unless a project constraint requires another tool.
3. Add Python version constraint.
4. Add Ruff formatting/linting.
5. Add Pytest.
6. Add mypy or equivalent type checking where useful.
7. Add Pydantic.
8. Add Typer for CLI.
9. Add structured logging.
10. Implement configuration loading.
11. Implement filesystem project store.
12. Implement health checks.
13. Detect Apple Silicon.
14. Detect Ollama.
15. Detect FFmpeg.
16. Add memory/disk preflight checks.
17. Document setup.

## Commands

```bash
video-agent health
video-agent doctor
```

## Acceptance criteria

`doctor` reports:

- OS
- Architecture
- Python
- available memory
- Ollama status
- installed Ollama models
- FFmpeg status/version
- writable project directory
- available disk space

---

# 9. Phase 1 — Local LLM Director

## Goal

Generate structured production specifications using a local LLM.

## LLM boundary

Create:

```python
class LLMProvider(Protocol):
    def generate(self, request: LLMRequest) -> LLMResponse: ...
```

Ollama becomes the initial implementation.

## Required behavior

The Director must never trust raw LLM output blindly.

Pipeline:

```text
Prompt
  ↓
LLM
  ↓
JSON extraction
  ↓
Pydantic validation
  ↓
repair/retry if invalid
  ↓
validated project
```

## Tasks

- Ollama HTTP client
- Configurable model
- Temperature/top-p/top-k configuration where supported
- Structured JSON prompting
- Output validation
- Retry policy
- Prompt version tracking
- Token/output logging without storing sensitive content unnecessarily

## Acceptance criteria

Example:

```bash
video-agent create "Explain AI agents" --duration 60
```

creates a valid `project.json` and `brief.json`.

---

# 10. Phase 2 — Script and Storyboard Engine

## Goal

Produce a complete scene plan before expensive generation starts.

## Script requirements

Script must respect:

- requested duration
- speaking pace
- language
- intended audience
- tone
- structure

## Storyboard requirements

Each scene must specify:

- time range
- narration
- visual objective
- image prompt
- motion prompt
- camera
- framing
- lighting
- continuity references
- preferred provider
- fallback provider

## Validation rules

- Scene durations sum to approximately total duration.
- Narration length is compatible with scene duration.
- No missing required prompts.
- No overlapping scene intervals.
- No negative durations.

## Acceptance criteria

A storyboard can be passed directly to the asset generation stage without manual prompt writing.

---

# 11. Phase 3 — Image Generation

## Goal

Generate scene images locally.

## Provider abstraction

```python
class ImageProvider(Protocol):
    def generate(self, request: ImageGenerationRequest) -> ImageResult: ...
```

Provider request should include:

- prompt
- negative prompt
- width
- height
- seed
- steps
- guidance/settings
- model
- style references

## Backend strategy

Start with a local backend that is practical on Apple Silicon. Keep the interface compatible with ComfyUI and other local backends so the backend can change later without changing the application.

## Tasks

- Provider implementation
- Generate one image per scene
- Save seed and parameters
- Validate dimensions
- Generate preview
- Detect corrupt files
- Retry failed scenes
- Add per-scene regeneration

## Acceptance criteria

```bash
video-agent generate-scene <project-id> scene-01
```

produces an image plus generation metadata.

---

# 12. Phase 4 — Local TTS

## Goal

Generate professional-enough narration locally.

## Interface

```python
class TTSProvider(Protocol):
    def synthesize(self, request: TTSRequest) -> AudioResult: ...
```

## Tasks

- Voice registry
- Voice selection
- Per-scene synthesis
- WAV/standard intermediate format
- Sample-rate normalization
- Loudness normalization
- Silence trimming only where safe
- Actual duration measurement
- Concatenation
- Voice metadata persistence

## Acceptance criteria

The whole storyboard can be synthesized into one narration track and timing data is available for subtitle generation.

---

# 13. Phase 5 — Subtitle and Timeline Engine

## Goal

Construct a deterministic timeline from scene and audio metadata.

## Tasks

- Scene timing engine
- Subtitle segmentation
- SRT generation
- Optional WebVTT generation
- Image motion effects
- Crossfade support
- Intro/outro
- Background music track
- Ducking for narration
- Audio fade-in/out

## Important rule

The timeline is data-driven. FFmpeg should execute a generated render plan; application logic should not contain hard-coded one-off shell commands for every video.

## Render plan

Example concept:

```json
{
  "resolution": "1920x1080",
  "fps": 24,
  "scenes": [
    {
      "asset": "scene-01.png",
      "duration": 5,
      "effect": "ken-burns"
    }
  ],
  "audio": "narration.wav",
  "subtitles": "subtitles.srt"
}
```

---

# 14. Phase 6 — FFmpeg Renderer

## Goal

Produce a valid MP4 from the timeline.

## Requirements

- H.264 output initially
- Standard audio codec
- Configurable FPS
- Configurable resolution
- Safe filenames/path escaping
- Hardware-accelerated options where practical
- Render metadata
- Output validation

## Validation

After rendering:

- File exists
- File is readable
- Duration approximately matches expected duration
- Video stream exists
- Audio stream exists when expected
- Resolution matches requested output

## Acceptance criteria

The first complete end-to-end video is produced from still images and local narration.

---

# 15. Phase 7 — AI Video Generation

## Goal

Introduce actual generated motion clips without destabilizing the existing system.

## Strategy

Image-to-video first. Text-to-video can follow.

Why:

- Existing storyboard images provide composition anchors.
- It is easier to maintain visual continuity.
- A static-image fallback remains available.

## Provider interface

```python
class VideoProvider(Protocol):
    def generate(self, request: VideoGenerationRequest) -> VideoResult: ...
```

## Tasks

1. Evaluate local Apple-Silicon-compatible video runtimes/models.
2. Prefer short clips initially.
3. Define model capability metadata.
4. Add image-to-video provider.
5. Generate 3–10 second clips.
6. Validate generated video.
7. Add scene-level fallback to image animation.
8. Add cache keyed by request hash.

## Acceptance criteria

A project may contain:

```text
scene 1 -> generated image + motion
scene 2 -> generated video
scene 3 -> generated image + motion
scene 4 -> generated video
```

and produce one final MP4.

---

# 16. Phase 8 — Scene-Level Intelligence

## Goal

Let the Director decide how each scene should be rendered.

Each scene should have:

```text
media_strategy:
    STATIC_IMAGE
    IMAGE_MOTION
    IMAGE_TO_VIDEO
    TEXT_TO_VIDEO
```

Decision factors:

- Importance of motion
- Duration
- Provider availability
- Quality profile
- Current memory availability
- Generation cost/time
- Continuity requirements

The decision engine should be rule-based initially. LLM-assisted decisions can be introduced later and must remain bounded by application policies.

---

# 17. Phase 9 — Quality Assurance Engine

## Goal

Detect bad outputs before final rendering.

## Image checks

- File integrity
- Dimensions
- Aspect ratio
- Black/blank image detection where feasible
- Minimum file size

## Video checks

- Decode succeeds
- Duration valid
- Expected resolution
- No zero-duration output

## Audio checks

- Decode succeeds
- Duration valid
- Silence/anomaly detection where practical
- Loudness normalization

## Project checks

- Every scene has required asset
- All scene durations accounted for
- Subtitle timing valid
- Final duration within tolerance

## Acceptance criteria

The pipeline blocks obviously invalid projects and identifies the exact artifact/scene requiring regeneration.

---

# 18. Phase 10 — Agentic Recovery and Refinement

## Goal

Add bounded autonomy.

The agent may:

1. Detect failure.
2. Classify failure.
3. Attempt a safe corrective action.
4. Regenerate only the affected artifact.
5. Revalidate.
6. Escalate to the user when the retry budget is exhausted.

## Retry budgets

Never allow infinite generation loops.

Example:

```text
image generation retries: 2
video generation retries: 2
LLM JSON repair attempts: 2
render retries: 1
```

## Refinement examples

If narration exceeds scene duration:

```text
rewrite narration → validate → regenerate TTS
```

If image generation fails:

```text
simplify prompt → retry → fallback provider → fallback to previous/cached asset
```

If video generation exceeds memory:

```text
lower resolution → reduce clip duration → fallback to image motion
```

---

# 19. Phase 11 — Web API and UI

## API

FastAPI endpoints:

```text
POST /projects
GET  /projects/{project_id}
POST /projects/{project_id}/plan
POST /projects/{project_id}/generate
POST /projects/{project_id}/scenes/{scene_id}/generate
POST /projects/{project_id}/render
POST /projects/{project_id}/resume
GET  /projects/{project_id}/artifacts
GET  /projects/{project_id}/events
GET  /health
GET  /providers
```

## UI

Initial UI should expose only high-value controls:

- Prompt
- Duration
- Aspect ratio
- Style
- Language
- Voice
- Quality
- Generate
- Scene list
- Scene preview
- Regenerate scene
- Render
- Final video preview

Do not expose all model parameters initially. Advanced configuration can be added later.

---

# 20. Phase 12 — Persistence and Job Management

## Initial storage

Filesystem + JSON manifests.

This avoids unnecessary database complexity.

## Later storage

SQLite for:

- projects
- generation runs
- provider metadata
- status
- artifact index

## Job lifecycle

```text
QUEUED
RUNNING
WAITING
COMPLETED
FAILED
CANCELLED
```

## Resume behavior

On restart:

1. Load project manifest.
2. Detect completed artifacts.
3. Verify hashes/files.
4. Mark missing/corrupt artifacts as incomplete.
5. Resume from first incomplete stage.

---

# 21. Phase 13 — Caching

Cache deterministic or expensive provider calls.

Cache key should include:

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

Never silently reuse a stale output when the generation configuration changed.

Expose:

```bash
video-agent cache stats
video-agent cache clear
video-agent cache clear-project <id>
```

---

# 22. Phase 14 — Model and Provider Registry

Maintain a registry containing capability metadata.

Example:

```text
provider: local-video-a
capabilities:
  image_to_video: true
  text_to_video: false
  max_duration: 5
  preferred_resolution: 512x512
  memory_class: high
```

The scene planner uses this information when selecting a provider.

---

# 23. Phase 15 — Evaluation Framework

Create a repeatable benchmark set with fixed prompts.

Example benchmark categories:

1. Educational explainer
2. Product advertisement
3. Cinematic scene
4. Social-media short
5. Technical tutorial
6. Storytelling scene
7. Character continuity

Measure:

- Planning validity
- Generation success rate
- Render success rate
- Average generation time
- Memory failures
- Artifact reuse rate
- Scene regeneration rate
- Final duration accuracy

Later add human-quality ratings for:

- Visual relevance
- Prompt adherence
- Narrative quality
- Audio quality
- Temporal consistency

---

# 24. Phase 16 — Security and Safety

Even though the system is local, establish boundaries.

## File safety

- Restrict project paths
- Prevent arbitrary path traversal
- Sanitize user filenames
- Avoid unsafe shell interpolation

## Process safety

- Use subprocess argument arrays rather than shell strings
- Time-limit external processes
- Capture stdout/stderr
- Terminate failed processes cleanly

## Content policy hooks

The architecture should allow a policy/validation layer before expensive generation. The implementation must follow applicable model and software licenses and must not bypass provider safeguards.

---

# 25. Testing Strategy

## Unit tests

Cover:

- Pydantic schemas
- Duration calculations
- Timeline generation
- Artifact hashing
- Cache keys
- Provider selection
- Retry rules
- Configuration

## Integration tests

Use mocked providers for most CI tests.

Examples:

- LLM → storyboard
- storyboard → mock image provider
- storyboard → mock TTS
- timeline → FFmpeg fixture

## Hardware tests

Run local Apple Silicon tests separately for:

- Ollama
- actual image model
- actual TTS
- actual video model

Do not require heavyweight local models in ordinary unit-test CI.

---

# 26. Observability

Every generation should have a correlation ID.

Example log context:

```text
project_id=abc123
run_id=run-004
scene_id=scene-03
stage=image_generation
provider=local-image
model=model-x
```

Structured logs should make it possible to answer:

- What failed?
- Which scene failed?
- Which model was used?
- What input produced it?
- How long did it take?
- Which artifact was created?

---

# 27. Error Taxonomy

Define explicit errors instead of generic exceptions.

```text
ConfigurationError
ProviderUnavailableError
ModelNotFoundError
InvalidLLMOutputError
SchemaValidationError
GenerationError
ArtifactValidationError
RenderError
OutOfMemoryRiskError
InsufficientDiskError
CancellationError
```

Errors should include:

- stage
- provider
- scene
- recoverable flag
- suggested action

---

# 28. Configuration

Example configuration concept:

```yaml
runtime:
  profile: balanced
  max_concurrent_media_jobs: 1

llm:
  provider: ollama
  model: qwen2.5-coder:32b
  temperature: 0.2

image:
  provider: local
  model: default

video:
  provider: local
  model: default
  enabled: false

tts:
  provider: local
  voice: default

render:
  fps: 24
  codec: h264
  audio_codec: aac

storage:
  root: ./data
```

The actual default model should be selected based on measured performance, not assumed permanently in source code.

---

# 29. Prompt Engineering Structure

Prompts should be versioned files, not large strings embedded in Python.

Example:

```text
prompts/
├── system/
│   └── director_v1.txt
├── director/
│   ├── brief_v1.txt
│   ├── script_v1.txt
│   └── storyboard_v1.txt
├── scene/
│   ├── image_v1.txt
│   └── motion_v1.txt
└── quality/
    └── review_v1.txt
```

Persist the prompt version with every generation run.

---

# 30. Versioning Strategy

Project files must include a schema version.

Example:

```json
{
  "schema_version": "1.0",
  "project_id": "abc123"
}
```

When schemas change, provide migrations instead of silently breaking old projects.

---

# 31. Initial Model Strategy

The initial local LLM layer should use the existing Ollama environment where possible.

Recommended role separation:

- Small/fast model: simple transformations, metadata, lightweight repairs
- Stronger local model: creative planning, script, storyboard, complex prompt generation

The application should not hard-code Qwen or Llama semantics. Both should implement the same LLM interface.

The image/video/TTS models should similarly be swappable.

---

# 32. First Vertical Slice

Before building every abstraction, implement one complete vertical slice:

```text
User prompt
   ↓
Ollama
   ↓
project.json
   ↓
storyboard.json
   ↓
3 test images
   ↓
TTS
   ↓
subtitles.srt
   ↓
FFmpeg
   ↓
final.mp4
```

This is the first major engineering proof point.

Do not proceed to advanced video models until this works reliably.

---

# 33. Milestones

## M0 — Foundation

Exit criteria:

- Repository builds
- Tests execute
- `doctor` works
- Ollama detected
- FFmpeg detected

## M1 — Director

Exit criteria:

- Natural language input
- Valid creative brief
- Valid script
- Valid storyboard

## M2 — First Video

Exit criteria:

- Local image assets
- Local narration
- Subtitles
- Final MP4

## M3 — AI Motion

Exit criteria:

- At least one local motion provider
- Scene-level motion generation
- Static fallback

## M4 — Reliability

Exit criteria:

- Retry handling
- Resume support
- Artifact validation
- Cache

## M5 — User Product

Exit criteria:

- CLI stable
- API available
- Local UI available

## M6 — Video Agent

Exit criteria:

- Automatic scene strategy
- Quality checks
- Bounded refinement
- Provider routing

---

# 34. Definition of V1

V1 is complete when this works:

```bash
video-agent create "Create a 60-second educational video explaining AI agents" \
  --duration 60 \
  --style cinematic
```

and results in:

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

Requirements:

- Runs locally
- No paid cloud inference requirement
- Can regenerate one scene
- Can resume a failed job
- Produces valid final MP4
- Preserves generation metadata

---

# 35. Definition of V2 — AI Motion

V2 adds:

- Image-to-video provider
- Scene-level media strategy
- Generated motion clips
- Fallback to animated stills
- Provider capability registry
- Quality validation for video assets

---

# 36. Definition of V3 — Video Agent

V3 adds:

- Automatic provider selection
- Quality evaluator
- Retry/repair loops
- Prompt refinement
- Narration correction
- Resume after interruption
- Local web UI
- Project history

---

# 37. Non-Goals for Early Development

Do not initially build:

- Multi-user SaaS authentication
- Kubernetes
- Distributed inference
- GPU cluster orchestration
- Custom foundation-model training
- Custom video codecs
- Complex microservices
- Cloud dependency in the core path
- Fully autonomous unrestricted agent loops

These can be revisited after the single-machine pipeline is proven.

---

# 38. Recommended Implementation Sequence

Implement in this order:

1. Python project foundation
2. Configuration
3. Logging
4. Health/doctor command
5. Pydantic project/scene/artifact schemas
6. Filesystem storage
7. Ollama adapter
8. Director prompt
9. Creative brief generation
10. Script generation
11. Storyboard generation
12. Storyboard validation
13. Image provider interface
14. First local image backend
15. Scene image generation
16. TTS interface
17. First local TTS backend
18. Subtitle generation
19. Timeline builder
20. FFmpeg renderer
21. Final-video validation
22. End-to-end CLI
23. Resume support
24. Per-scene regeneration
25. Artifact caching
26. Video provider interface
27. First local image-to-video backend
28. Scene-level strategy selection
29. Quality evaluator
30. Retry/repair engine
31. FastAPI
32. Local UI
33. SQLite/job history
34. Benchmark suite
35. Performance optimization

---

# 39. First Implementation Checklist

The first coding session should implement only:

- [ ] `pyproject.toml`
- [ ] package layout
- [ ] config loader
- [ ] logging
- [ ] `video-agent health`
- [ ] `video-agent doctor`
- [ ] Pydantic `VideoProject`
- [ ] Pydantic `Scene`
- [ ] filesystem project store
- [ ] Ollama health check
- [ ] FFmpeg health check
- [ ] one Ollama generation call
- [ ] one valid JSON project output

The first coding milestone is **not** video generation. The first milestone is a reliable local control plane that can talk to Ollama and manage project state.

---

# 40. Engineering Rules for This Repository

1. Keep provider integrations isolated.
2. Keep business logic independent of concrete model names.
3. Never store generated binaries in Git.
4. Persist metadata for every expensive generation.
5. Validate external/model output at boundaries.
6. Use retries only for explicitly recoverable errors.
7. Never create infinite agent loops.
8. Prefer deterministic application logic over unnecessary LLM calls.
9. Keep prompts versioned.
10. Make every stage independently rerunnable.
11. Add tests before refactoring core data models.
12. Measure memory and generation time on the actual M4 hardware.
13. Optimize only after an end-to-end baseline exists.
14. Prefer a working simple pipeline over a sophisticated incomplete architecture.

---

# 41. Long-Term Architecture

The eventual platform should look like:

```text
                        ┌──────────────────┐
                        │    User / UI     │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │   Project API    │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │ Video Director   │
                        │   Local LLM      │
                        └────────┬─────────┘
                                 │
                      ┌──────────▼──────────┐
                      │  Planning / State   │
                      └──────────┬──────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
        Image Agent         Video Agent         Audio Agent
              │                  │                  │
              ▼                  ▼                  ▼
         Image Model        Video Model          TTS
              │                  │                  │
              └──────────────────┼──────────────────┘
                                 ▼
                         ┌───────────────┐
                         │ Quality Agent │
                         └───────┬───────┘
                                 │
                         ┌───────▼───────┐
                         │ Editor/Render │
                         │    FFmpeg     │
                         └───────┬───────┘
                                 │
                                 ▼
                              final.mp4
```

The important architectural boundary is that **the LLM decides and coordinates; deterministic software validates, executes, stores, and renders**.

---

# 42. Project Success Criteria

The project is successful when a user can stay on the M4 Mac, type a natural-language video request, and receive a reproducible MP4 without manually assembling scripts, images, audio, subtitles, and editing steps.

The system should remain understandable enough that an engineer can inspect any intermediate artifact, replace one model/provider, rerun a failed scene, and reproduce the final render from the saved project manifest.
