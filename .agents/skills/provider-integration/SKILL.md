# Provider Integration Skill

## Scope

Use for Ollama, image, video, TTS, music, embedding, or rendering provider integrations.

## Required Boundary

```text
Application -> Provider Interface -> Adapter -> Runtime/SDK
```

Application code must not depend directly on a provider SDK.

## Provider Checklist

- [ ] Interface exists or is reused.
- [ ] Capability metadata is defined.
- [ ] Configuration is externalized.
- [ ] Health check exists.
- [ ] Errors map to domain errors.
- [ ] Resource requirements are documented.
- [ ] Input validation exists.
- [ ] Output validation exists.
- [ ] Retries are bounded.
- [ ] Tests cover success and failure paths.
- [ ] Fallback is documented.
- [ ] Model/provider version metadata is persisted.

## Model Metadata

Persist where available:

- provider name
- model name
- model version/revision
- precision/quantization
- seed
- prompt version
- generation parameters

## Hardware Awareness

Provider selection must account for the M4/36 GB target. Do not assume CPU/GPU memory is independent on Apple Silicon.

## Failure Policy

A provider failure should become a normalized error containing:

- provider
- model
- stage
- recoverable
- reason
- suggested fallback

Never conceal a provider failure behind a successful-looking artifact.
