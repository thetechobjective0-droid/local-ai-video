# Testing Strategy

## Objective

Maintain a reliable test system for a local AI/media pipeline where real model execution is expensive and hardware-dependent.

## Test Layers

### Unit

Fast tests with no external model/runtime requirement.

Scope:

- Pydantic models
- configuration
- prompt rendering
- duration calculations
- timeline generation
- artifact manifests
- hashing
- cache keys
- retry policies
- provider routing
- path validation

### Contract

Verify that every provider adapter conforms to the normalized provider interface.

Each adapter should be testable against a fake runtime or deterministic fixture.

### Integration

Verify interactions between application stages.

Examples:

```text
Director -> Storyboard validator
Storyboard -> Image provider adapter
Storyboard -> TTS adapter
Artifacts -> Timeline
Timeline -> FFmpeg
```

### End-to-End

Maintain a small deterministic pipeline using test/fake providers:

```text
prompt
 -> fixed project
 -> fixed images
 -> fixed audio
 -> subtitles
 -> FFmpeg
 -> final fixture video
```

The E2E test must not require downloading large models.

### Hardware

Run actual Ollama/image/video/TTS model tests separately on Apple Silicon.

Suggested markers:

```text
@pytest.mark.hardware
@pytest.mark.models
@pytest.mark.slow
```

## Required Test Cases

### Project tests

- Valid project accepted.
- Zero duration rejected.
- Negative duration rejected.
- Unsupported aspect ratio rejected.
- Duplicate scene IDs rejected.
- Overlapping scenes rejected.
- Scene total duration mismatch detected.

### LLM tests

- Valid structured response accepted.
- Markdown-wrapped JSON parsed correctly where supported.
- Invalid JSON rejected or repaired.
- Missing required field rejected.
- Wrong field type rejected.
- Excessive scene count rejected.
- Malicious instructions inside LLM output never execute.

### Image tests

- Valid image accepted.
- Corrupt image rejected.
- Wrong dimensions rejected when strict mode is enabled.
- Cache hit returns existing valid artifact.
- Changed prompt invalidates cache.
- Changed seed invalidates cache.
- Provider failure maps to typed error.

### Video tests

- Valid clip accepted.
- Corrupt clip rejected.
- Invalid duration rejected.
- Unsupported resolution handled.
- Image-motion fallback works.
- Provider timeout is recoverable.
- Retry count is bounded.

### TTS tests

- Valid audio accepted.
- Invalid audio rejected.
- Empty narration handled intentionally.
- Actual duration recorded.
- Excessive narration is detected before final render.

### Render tests

- Deterministic render plan for equivalent inputs.
- Invalid timeline rejected before FFmpeg execution.
- FFmpeg non-zero exit becomes RenderError.
- Final video contains expected video stream.
- Final video contains audio when audio is configured.
- Final duration is within tolerance.
- Expected resolution and FPS are validated.

### Storage tests

- Project stays under configured root.
- `../` traversal rejected.
- Missing artifact detected on resume.
- Corrupt artifact detected by hash/validation.
- Manifest updates are atomic where practical.

## Regression Policy

Every production bug in deterministic code must receive a regression test.

For model-quality failures that cannot be reliably tested semantically, add a structured fixture/constraint test wherever possible.

## Test Data

Keep reusable fixtures under:

```text
tests/fixtures/
```

Do not store large model weights or large generated media in the repository.

## CI Expectations

CI should run:

1. formatter check
2. linter
3. type checks where configured
4. unit tests
5. contract tests
6. lightweight integration tests

Heavy model/hardware suites should be separate.
