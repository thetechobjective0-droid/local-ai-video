# Phase 4 — Local TTS Status

## Implemented

- Provider-agnostic `TTSProvider` protocol.
- Typed `TTSRequest` and `TTSResult` contracts.
- macOS built-in Speech (`say`) provider for fully local narration.
- Configurable local voice, speech rate, and sample rate.
- Scene-level narration synthesis service.
- WAV integrity and duration validation.
- SHA-256 output verification.
- Persistent `scene_audio` artifact metadata.
- Scene `audio_asset` linkage.
- CLI command: `video-agent generate-audio <project-id> <scene-id>`.
- Fake-provider regression coverage that does not require macOS in CI.

## Local M4 acceptance

Run on the target Mac:

```bash
video-agent generate-audio <project-id> <scene-id>
```

Verify that the generated WAV decodes and that the persisted artifact contains provider, model, voice, sample rate, channel count, duration, and SHA-256 metadata.

The repository remains local-first: the Phase 4 implementation does not call a cloud TTS service or upload narration text.
