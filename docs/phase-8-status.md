# Phase 8 — Scene-Level Media Strategy

## Status

**IN PROGRESS**

Phase 8 now has deterministic routing, centralized provider capabilities, and project-level media orchestration.

## Implemented

- `VideoCapability` defines provider capabilities and conservative limits.
- `select_media_type()` chooses media deterministically from scene preference, fallback, provider capability, duration limits, and an optional available-memory signal.
- A centralized provider capability registry defines the supported LTX and FFmpeg profiles.
- `generate_project_media()` can resolve capabilities from the concrete provider instead of requiring CLI-local declarations.
- Explicit `IMAGE_MOTION` routing is restricted to providers that advertise deterministic motion capability.
- Image-to-video generation is attempted when selected.
- Provider failure can fall back to deterministic image motion when a fallback provider is supplied.
- Selected strategy and fallback usage are persisted in scene metadata.
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

The orchestration layer now resolves registered capabilities from the provider when a capability object is not explicitly supplied.

## Important limitation

The current orchestrator assumes scene images have already been generated. It does not yet invoke the image provider itself. This keeps image generation and media routing independently rerunnable.

The CLI still accepts an optional `--memory-gb` override. Real host resource snapshots are the next routing improvement.

## Next

1. Integrate real resource snapshots instead of an optional CLI memory value.
2. Add cache keys around strategy inputs and generated artifacts.
3. Add project state transitions for `ASSETS_GENERATING` and `ASSETS_READY`.
4. Add video QA before an AI clip is accepted as renderable.
5. Preserve the deterministic fallback path when AI video generation is unavailable or fails.
6. Remove duplicated provider construction/capability knowledge from CLI wiring once the provider factory is centralized.

## Acceptance

Hardware acceptance remains pending on the target M4 Mac. CI should validate the deterministic routing and orchestration boundaries; actual LTX model loading, memory consumption, generation latency, and visual quality require the target machine and locally stored model weights.
