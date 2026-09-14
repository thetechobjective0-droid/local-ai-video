# Local AI Video Generator — Project Plan

## 1. Project Goal

Build a local-first AI video generation system that runs primarily on an Apple Silicon Mac (M4, 36 GB unified memory) and uses a local LLM as the orchestration layer.

The system should accept a natural-language request such as:

> Create a 60-second cinematic video explaining how AI agents work.

and progressively automate:

1. Creative brief and requirements extraction
2. Script generation
3. Storyboard / scene planning
4. Image and/or video prompt generation
5. Local image generation
6. Local voice generation
7. Subtitle generation
8. Video composition
9. AI image-to-video / text-to-video generation
10. Final MP4 rendering

The architecture must remain model-agnostic so individual models can be replaced without redesigning the application.

---

## 2. Hardware Target

Primary development target:

- Apple Mac with M4
- 36 GB unified memory
- Apple Silicon / Metal acceleration where supported
- Local inference preferred
- Cloud APIs optional, never required for the core pipeline

### Hardware constraint

The 36 GB unified-memory limit means the project should avoid assuming that very large video-generation models can run comfortably. The pipeline should support lightweight and medium-sized models and allow components to be swapped as better Apple-Silicon-compatible implementations become available.

---

## 3. Guiding Principles

### Local-first

The default workflow should run locally. Network access should only be required for initial model downloads, dependency installation, or explicitly selected optional services.

### Model-agnostic

LLM, image, video, TTS, and embedding models must be accessed through adapters/interfaces rather than hard-coded throughout the application.

### Pipeline-oriented

Every phase should produce inspectable intermediate artifacts. A failed video render should not require rerunning the entire project.

### Deterministic where possible

Seeds, model configuration, prompts, and generated metadata should be persisted so results can be reproduced.

### Incremental development

Build a useful image-based video generator first. Add actual AI video generation only after the core pipeline is stable.

---

# 4. Phase Plan

## Phase 0 — Architecture & Environment

### Objective

Establish the repository, development environment, configuration structure, model abstraction, and project conventions.

### Tasks

- Create Python project structure.
- Establish virtual environment / package management.
- Add configuration management through environment variables and config files.
- Add structured logging.
- Add project/job identifiers.
- Define artifact directory conventions.
- Define provider interfaces for LLM, image, video, TTS, and composition.
- Confirm Ollama connectivity.
- Confirm FFmpeg availability.
- Add basic health checks.
- Document Apple Silicon setup.

### Deliverables

- Working Python application skeleton.
- `config.example.yaml` or equivalent.
- Health-check command.
- Local development setup documentation.

### Acceptance criteria

```bash
python -m app health
```

reports the local runtime, Ollama availability, FFmpeg availability, and configured model providers.

---

## Phase 1 — Local LLM Video Director

### Objective

Use the local LLM as the project's creative director / orchestration layer.

### Initial model

Use an existing Ollama model where practical. The current development environment already includes Qwen models, so the first implementation should support Qwen through Ollama. Llama should remain a supported alternative.

### Tasks

- Build Ollama client.
- Implement structured LLM output.
- Define video project schema.
- Generate title, target audience, tone, duration, aspect ratio, style, narration, and scene count.
- Validate LLM JSON output.
- Implement retry / repair for malformed JSON.

### Deliverables

Example:

```json
{
  "project_id": "demo-001",
  "title": "How AI Agents Work",
  "duration_seconds": 60,
  "aspect_ratio": "16:9",
  "style": "cinematic educational",
  "scenes": []
}
```

### Acceptance criteria

A natural-language topic produces a valid project JSON document with no manual editing.

---

## Phase 2 — Storyboard & Prompt Engine

### Objective

Convert the project brief into a production-ready scene plan.

### Tasks

- Generate scene-by-scene storyboard.
- Define scene duration.
- Define narration per scene.
- Define visual intent.
- Generate image prompts.
- Generate motion prompts.
- Generate negative prompts where supported.
- Define camera direction, composition, lighting, and style.
- Maintain character / subject consistency metadata.

### Scene schema

Each scene should support:

```text
scene_id
start_time
duration
narration
visual_description
image_prompt
motion_prompt
negative_prompt
camera
style
asset_requirements
```

### Acceptance criteria

A 60-second request produces a complete storyboard that can be rendered without additional creative decisions.

---

## Phase 3 — Local Image Generation

### Objective

Produce visual assets for every scene using a locally accessible image-generation backend.

### Candidate architecture

Prefer a backend abstraction that can later support ComfyUI or another local generation runtime.

### Tasks

- Define image-generation provider interface.
- Integrate first local backend.
- Generate scene images.
- Persist prompts, seeds, model names, and parameters.
- Add image dimension / aspect-ratio handling.
- Add retries and failed-scene recovery.
- Generate thumbnails / previews where useful.

### Acceptance criteria

Every storyboard scene can produce a local image asset and corresponding metadata.

---

## Phase 4 — Voice / TTS

### Objective

Convert scene narration into a locally generated voice track.

### Tasks

- Define TTS provider interface.
- Select a practical local TTS engine for Apple Silicon.
- Generate per-scene audio.
- Normalize audio volume.
- Track voice configuration.
- Concatenate scene audio.
- Calculate actual durations.
- Support multiple voices later.

### Acceptance criteria

A project can generate a complete narration track from scene narration with no cloud API requirement.

---

## Phase 5 — Video Assembly

### Objective

Combine generated images, narration, transitions, subtitles, and optional music into a valid video.

### Primary technology

FFmpeg.

### Tasks

- Convert scene images into timed video segments.
- Apply basic motion (pan / zoom / Ken Burns style) where appropriate.
- Concatenate scenes.
- Add narration.
- Generate subtitles from the storyboard.
- Add optional background music.
- Add title / end card.
- Render MP4.
- Persist render metadata.

### V1 output

```text
final.mp4
```

### Acceptance criteria

A 30–60 second project can be rendered end-to-end from generated still images and narration.

---

## Phase 6 — AI Image-to-Video / Text-to-Video

### Objective

Replace selected static scenes with actual AI-generated motion clips.

### Strategy

Do not redesign the application. Add a video-generation provider implementing the same provider interface.

### Tasks

- Evaluate Apple-Silicon-compatible local video models.
- Evaluate ComfyUI-based workflows.
- Start with short clips.
- Support image-to-video first where practical.
- Generate 3–10 second scene clips.
- Add clip interpolation / extension strategy where needed.
- Add fallback to static-image animation when video generation fails.

### Acceptance criteria

At least one project can contain a mixture of:

- AI-generated video clips
- Generated still images with motion
- Audio narration

and render to a single MP4.

---

## Phase 7 — Consistency & Quality

### Objective

Improve visual consistency, audio quality, prompt quality, and production reliability.

### Tasks

- Character / subject reference support.
- Style locking.
- Seed management.
- Prompt templates.
- Scene continuity.
- Audio loudness normalization.
- Subtitle timing correction.
- Aspect-ratio presets.
- Quality profiles: fast / balanced / quality.
- Automatic validation of generated assets.

### Acceptance criteria

Repeated renders with the same saved project configuration are sufficiently reproducible and production metadata is complete.

---

## Phase 8 — CLI, API & Web UI

### Objective

Make the pipeline easy to use instead of requiring Python code changes.

### CLI target

```bash
video-agent create "Explain how an AI agent works" --duration 60
```

### API target

```text
POST /projects
POST /projects/{id}/generate
GET  /projects/{id}
GET  /projects/{id}/artifacts
POST /projects/{id}/render
```

### UI target

Simple local web interface with:

- Prompt box
- Duration
- Style
- Aspect ratio
- Voice
- Quality profile
- Scene preview
- Render progress
- Download button

### Candidate UI stack

Start with a lightweight Python web UI such as Gradio or a small FastAPI frontend. Keep the backend independent from the UI.

### Acceptance criteria

A non-developer can create a video from a browser on the local Mac.

---

## Phase 9 — Agentic Automation

### Objective

Turn the pipeline into a genuine video-production agent rather than a simple sequential script.

### Capabilities

- Determine which generation method is best for each scene.
- Retry failed generation.
- Detect low-quality assets.
- Regenerate individual scenes.
- Rewrite weak narration.
- Improve prompts automatically.
- Compare outputs against project requirements.
- Maintain project state.
- Resume interrupted jobs.

### Example

```text
User request
    ↓
Director Agent
    ↓
Storyboard
    ↓
Scene Planner
    ↓
┌─────────────────────────┐
│ Scene 1 → Image         │
│ Scene 2 → Image-toVideo │
│ Scene 3 → Image         │
│ Scene 4 → Image-toVideo │
└─────────────────────────┘
    ↓
Voice Agent
    ↓
Editor Agent
    ↓
Quality Check Agent
    ↓
Final Render
```

### Acceptance criteria

The system can make reasonable production decisions without requiring the user to manually select the backend for every scene.

---

## Phase 10 — Production-grade Local Video Platform

### Objective

Turn the prototype into a maintainable local platform.

### Tasks

- Job queue.
- Persistent project database.
- Caching.
- Model registry.
- Provider health monitoring.
- Resource / memory checks.
- Parallel scene rendering where safe.
- Resume after interruption.
- Structured run history.
- Artifact versioning.
- Automated tests.
- CI checks.
- Documentation.

### Acceptance criteria

A user can maintain many video projects and safely resume or rerender individual stages.

---

# 5. Target Architecture

```text
                         ┌──────────────────────┐
                         │       User Input     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │    Video Director    │
                         │      (Local LLM)     │
                         └──────────┬───────────┘
                                    │
                           project / storyboard
                                    │
             ┌──────────────────────┼──────────────────────┐
             │                      │                      │
             ▼                      ▼                      ▼
      Image Provider          Video Provider          TTS Provider
             │                      │                      │
             └──────────────────────┼──────────────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   Render / Editor    │
                         │       FFmpeg         │
                         └──────────┬───────────┘
                                    │
                                    ▼
                               final.mp4
```

---

# 6. Proposed Repository Structure

```text
local-ai-video/
│
├── plan.md
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
│
├── app/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── logging.py
│   │
│   ├── models/
│   │   ├── project.py
│   │   ├── scene.py
│   │   └── artifact.py
│   │
│   ├── llm/
│   │   ├── base.py
│   │   └── ollama.py
│   │
│   ├── image/
│   │   ├── base.py
│   │   └── provider.py
│   │
│   ├── video/
│   │   ├── base.py
│   │   └── provider.py
│   │
│   ├── audio/
│   │   ├── base.py
│   │   └── tts.py
│   │
│   ├── render/
│   │   ├── ffmpeg.py
│   │   └── subtitles.py
│   │
│   ├── director/
│   │   ├── planner.py
│   │   ├── storyboard.py
│   │   └── prompts.py
│   │
│   └── pipeline/
│       ├── generate.py
│       └── orchestrator.py
│
├── prompts/
├── workflows/
├── tests/
├── scripts/
├── examples/
└── output/
```

---

# 7. Technology Direction

| Layer | Initial choice | Purpose |
|---|---|---|
| Language | Python | Fast local AI integration |
| LLM runtime | Ollama | Local model serving |
| LLM | Qwen initially; Llama supported | Planning and orchestration |
| Image generation | Provider abstraction, then local backend | Scene assets |
| Video generation | Provider abstraction, later ComfyUI/local model | Motion clips |
| TTS | Local TTS provider | Narration |
| Rendering | FFmpeg | Final composition |
| API | FastAPI later | Local service interface |
| UI | Gradio or lightweight frontend later | Local user interface |
| Storage | Files first; database later | Projects and artifacts |

---

# 8. Milestones

## Milestone M0 — Environment Ready

- Repository initialized
- Python project created
- Ollama connected
- FFmpeg connected
- Health check working

## Milestone M1 — Script Generator

- Natural language prompt accepted
- Structured video project generated
- Storyboard generated

## Milestone M2 — First Video

- Scene images generated
- Narration generated
- FFmpeg assembles MP4
- End-to-end command works

## Milestone M3 — AI Motion

- At least one local image-to-video backend integrated
- Mixed static + AI-motion project works

## Milestone M4 — Usable Product

- CLI stabilized
- Local web UI available
- Project persistence implemented

## Milestone M5 — Video Agent

- Automatic provider selection
- Quality checks
- Retry / repair loops
- Resume support

---

# 9. Definition of V1 Done

Version 1 is complete when the following command works:

```bash
video-agent create "Create a 60-second educational video explaining AI agents" \
  --duration 60 \
  --style cinematic
```

and produces:

```text
output/<project-id>/
├── project.json
├── storyboard.json
├── scenes/
│   ├── scene-01.png
│   ├── scene-02.png
│   └── ...
├── audio/
│   └── narration.wav
├── subtitles/
│   └── subtitles.srt
└── final.mp4
```

The entire V1 workflow should run locally using the available M4 machine and should not require a paid cloud inference API.

---

# 10. Implementation Order

Implement in this exact sequence to reduce unnecessary complexity:

1. Repository and Python skeleton
2. Configuration and logging
3. Ollama client
4. Project JSON schema
5. Script generator
6. Storyboard generator
7. Image provider interface
8. First local image backend
9. TTS provider interface
10. Local TTS backend
11. FFmpeg composition
12. End-to-end CLI
13. Subtitles
14. Project persistence
15. Video provider interface
16. First local image-to-video backend
17. Scene-level provider selection
18. Quality checks
19. Web UI
20. Agentic retry / refinement

Do not start with the web UI or complex multi-agent architecture. The first goal is a reliable end-to-end local render.

---

# 11. Non-Goals for Early Phases

Avoid these until the basic pipeline works:

- Cloud-only video generation
- Distributed inference
- Multi-user authentication
- Complex database architecture
- Kubernetes / container orchestration
- Training custom foundation models
- Building a custom video codec pipeline
- Building a custom GPU runtime

---

# 12. Engineering Standards

- Python type hints required for production code.
- Pydantic or equivalent schema validation for model outputs.
- Every generated artifact must have metadata.
- Errors should identify the phase and scene that failed.
- Each pipeline stage should be independently rerunnable.
- No hard-coded API credentials.
- No secrets committed to Git.
- Add unit tests for schemas, orchestration logic, and provider adapters.
- Add integration tests for Ollama and FFmpeg where practical.
- Keep model-specific code isolated behind interfaces.

---

# 13. Future Extensions

Potential future capabilities after the core system is stable:

- YouTube video mode
- Shorts / Reels / TikTok presets
- Automatic thumbnail generation
- Automatic title / description / tag generation
- Multi-language narration
- Lip-sync / talking avatar support
- Character consistency workflows
- Background music generation
- Sound-effect generation
- Automatic B-roll selection
- Video summarization and repurposing
- Long-form video generation
- Voice cloning where legally permitted
- Local embeddings / semantic asset search
- Project template system
- MCP integration
- Plugin architecture for new media models

---

# 14. Immediate Next Step

Start with **Phase 0** and implement the smallest working local pipeline:

```text
Prompt
  ↓
Ollama
  ↓
Structured project JSON
  ↓
Storyboard JSON
  ↓
Placeholder scene assets
  ↓
FFmpeg
  ↓
first.mp4
```

Once this works, replace placeholders with real image generation and continue through the phases above.
