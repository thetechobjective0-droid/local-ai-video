# Phase 8 — Scene-Level Media Strategy

## Status

**IN PROGRESS**

Phase 8 now has deterministic routing, centralized provider capabilities, project-level media orchestration, host resource snapshots, deterministic scene-video cache keys, and project asset lifecycle transitions.

## Implemented

- `VideoCapability` defines provider capabilities and conservative limits.
- `select_media_type()` chooses media deterministically from scene preference, fallback, provider capability, duration limits, and available-memory signal.
- A centralized provider capability registry defines the supported LTX and FFmpeg profiles.
- `generate_project_media()` resolves capabilities from the concrete provider when a capability object is not explicitly supplied.
- Project media generation captures a real host `ResourceSnapshot` when one is not explicitly provided.
- Resource snapshots record total memory, available memory, and free disk space in persisted scene metadata.
- Explicit `IMAGE_MOTION` routing is restricted to providers that advertise deterministic motion capability.
- Image-to-video generation is attempted when selected.
- Provider failure can fall back to deterministic image motion when a fallback provider is supplied.
- Selected strategy, fallback usage, routing memory, and resource snapshot are persisted in scene metadata.
- Scene-video generation derives a stable cache key from the input image hash, provider/model, prompts, dimensions, duration, FPS, and seed.
- Existing scene-video artifacts are reused only when the cache key and output SHA-256 both validate.
- Project media generation persists `ASSETS_GENERATING` before work, `ASSETS_READY` after all scenes succeed, and `FAILED` when generation raises.
- CLI command: `video-agent generate-media <PROJECT_ID>`.
- Unit coverage covers registry lookup and explicit motion capability routing.

## Current deterministic policy

```text
Scene preference
      |
      v
Provider capability + duration + memory gate
      |
      +--> IMAGE_TO_VIDEO --> provider succeeds --> use AI video
      |                         |
      |                         +--> fails --> IMAGE_MOTION fallback
      |
      +--> IMAGE_MOTION --> provider advertises motion --> deterministic motion
      |                  |
      |                  +--> unsupported --> STATIC_IMAGE
      |
      +--> STATIC_IMAGE ------------------------> existing image
      |
      +--> TEXT_TO_VIDEO -----------------------> explicit unsupported error
```

The LLM does not execute routing decisions directly. It can express scene intent through the validated Scene fields; application code decides what is actually safe and available.

## CLI

After storyboard and scene images exist:

```bash
uv run video-agent generate-media <PROJECT_ID>
```

The CLI no longer accepts a manual `--memory-gb` override. Resource-aware routing uses the host snapshot captured by the orchestrator.

## Cache policy

Scene-video caching is content-addressed by a deterministic generation key. The key includes the image input hash and all generation parameters that can affect the requested clip. A cache hit is accepted only when the persisted artifact manifest matches the key and the output file's SHA-256 matches the manifest.

This cache is intentionally conservative: it reuses the current scene-video artifact rather than introducing a global cross-project media store before cache eviction, statistics, and lifecycle rules are defined.

## Project lifecycle

Media generation now records explicit project-level lifecycle states:

```text
STORYBOARD_READY
       |
       v
ASSETS_GENERATING
       |
       +---- all scenes succeed ----> ASSETS_READY
       |
       +---- generation failure ----> FAILED
```

The transition is persisted atomically through `project.json`, and `updated_at` is refreshed on each transition.

## Important limitation

The current orchestrator assumes scene images have already been generated. It does not yet invoke the image provider itself. This keeps image generation and media routing independently rerunnable.

Hardware acceptance remains pending on the target M4 Mac. Resource snapshots use the host operating-system counters available to the Python runtime; actual model memory pressure and generation performance still require measurement on the target machine.

## Next

1. Add video QA before an AI clip is accepted as renderable.
2. Preserve and validate the deterministic fallback path when AI video generation is unavailable or fails.
3. Centralize provider construction so CLI wiring does not duplicate provider knowledge.
4. Expand caching into explicit project cache statistics/cleanup after lifecycle rules are defined.

## Acceptance

Hardware acceptance remains pending on the target M4 Mac. CI should validate deterministic routing, cache-key boundaries, lifecycle transitions, and orchestration behavior; actual LTX model loading, memory consumption, generation latency, and visual quality require the target machine and locally stored model weights.
