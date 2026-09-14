# Testing Skill

## Test Pyramid

Use the highest practical confidence at the lowest cost:

1. Unit tests
2. Contract tests
3. Integration tests
4. End-to-end tests
5. Hardware/model tests

## Required Cases

Every feature should consider:

- Happy path
- Empty input
- Invalid input
- Boundary values
- Dependency failure
- Retry behavior
- Cancellation
- Partial completion
- Resume behavior
- Corrupt artifact
- Configuration error

## Video-specific Test Cases

### Project

- Duration is positive.
- Scene durations sum to the project duration within an allowed tolerance.
- Scene indexes are unique and ordered.
- Scene intervals do not overlap.

### LLM

- Valid structured output is accepted.
- Invalid JSON is repaired/rejected.
- Missing required fields are rejected.
- LLM output cannot invoke arbitrary code.

### Image

- Provider returns a valid file.
- Corrupt output is rejected.
- Wrong dimensions are detected.
- Seed/configuration changes invalidate cache entries.

### Video

- Generated clip decodes.
- Duration is within configured bounds.
- Unsupported media is rejected.
- Fallback to static motion works.

### TTS

- Audio decodes.
- Duration is measured.
- Narration timing is compatible with scene duration.
- Silence/anomaly checks behave as expected.

### Render

- Render plan is deterministic for identical inputs.
- FFmpeg failure becomes a typed render error.
- Final MP4 has expected streams.
- Final duration is within tolerance.

## Regression Rule

Every defect fixed in core logic should receive a regression test that fails before the fix and passes after it.

## Hardware Tests

Heavy local model tests should be tagged separately. CI must not require large model downloads unless explicitly configured.
