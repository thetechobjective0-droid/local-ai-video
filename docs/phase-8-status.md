# Phase 8 — Scene-Level Media Strategy

## Status

**IN PROGRESS**

Phase 8 now has a deterministic routing layer and a project-level media orchestration slice.

## Implemented

- `VideoCapability` defines provider capabilities and conservative limits.
- `select_media_type()` chooses media deterministically from scene preference, fallback, provider capability, duration limits, and an optional available-memory signal.
- `generate_project_media()` applies the strategy across all scenes.
- Image-to-video generation is attempted when selected.
- Provider failure can fall back to deterministic image motion when a fallback provider is supplied.
- Selected strategy and fallback usage are persisted in scene metadata.
- CLI command: `video-agent generate-media <PROJECT_ID>`.
- Configured LTX and FFmpeg providers expose their Phase 8 capability profiles through the CLI wiring.
- Unit coverage was added for strategy selection and project-level fallback behavior.

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
      +--> IMAGE_MOTION ------------------------> deterministic motion
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

For an explicit memory signal:

```bash
uv run video-agent generate-media <PROJECT_ID> --memory-gb 12
```

## Important limitation

The current orchestrator assumes scene images have already been generated. It does not yet invoke the image provider itself. This keeps image generation and media routing independently rerunnable.

## Next

1. Add a formal provider capability registry instead of CLI-local capability declarations.
2. Integrate real resource snapshots instead of an optional CLI memory value.
3. Add cache keys around strategy inputs and generated artifacts.
4. Add project state transitions for `ASSETS_GENERATING` and `ASSETS_READY`.
5. Add video QA before an AI clip is accepted as renderable.
6. Preserve the deterministic fallback path when AI video generation is unavailable or fails.

## Acceptance

Hardware acceptance remains pending on the target M4 Mac. CI should validate the deterministic routing and orchestration boundaries; actual LTX model loading, memory consumption, generation latency, and visual quality require the target machine and locally stored model weights.
