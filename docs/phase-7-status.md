# Phase 7 — Video Provider Status

## Implemented

Phase 7 now has the first end-to-end video-provider boundary and scene-level orchestration:

- `VideoProvider` protocol with typed request/result models.
- Deterministic local `FFmpegVideoProvider` using a Ken Burns-style motion effect.
- Scene video generation orchestration in `app/generation/video.py`.
- Existing scene image artifact is required before video generation.
- Motion prompt and negative prompt are propagated into the provider request metadata.
- Generated video is SHA-256 verified before persistence.
- `scene_video` artifact metadata is persisted.
- `Scene.video_asset` is linked after successful generation.
- CLI command:

```bash
video-agent generate-video <PROJECT_ID> <SCENE_ID>
```

- Configurable provider and FPS in `config.example.yaml`.
- Unit coverage for scene video orchestration boundaries.

## Important distinction

`ffmpeg_ken_burns` is **not an AI video model**. It is the deterministic motion fallback required by the architecture. It gives the renderer a real video artifact while the actual Apple-Silicon-compatible AI image-to-video backend is evaluated and integrated behind the same `VideoProvider` interface.

## Current flow

```text
Scene storyboard
      ↓
Scene image artifact
      ↓
VideoProvider
      ↓
FFmpeg deterministic motion fallback
      ↓
scene-XXXX.mp4 + scene-video manifest
      ↓
Scene.video_asset
      ↓
Timeline / renderer
```

## Next Phase 7 work

1. Evaluate current local I2V runtimes/models for the M4 36 GB target.
2. Select a practical short-clip model based on memory, speed, quality, and local-runtime support.
3. Implement the selected AI provider without changing the scene-generation contract.
4. Add capability metadata and deterministic provider selection.
5. Add caching and resource-aware concurrency controls.
6. Validate mixed static-image, deterministic-motion, and AI-video scenes in the final renderer.

## Acceptance

Hardware acceptance must be run on the target M4 Mac. The repository cannot claim AI I2V performance or model compatibility until the selected model is actually exercised locally.
