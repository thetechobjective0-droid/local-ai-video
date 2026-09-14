# Performance Skill

## Goal

Keep the system usable on the target M4/36 GB unified-memory machine.

## Baseline First

Before optimization, record:

- operation
- provider/model
- input dimensions
- duration
- wall-clock time
- peak memory if measurable
- output size

## Rules

- Default heavyweight media concurrency to 1.
- Avoid loading multiple large models unnecessarily.
- Release resources between incompatible heavyweight providers where possible.
- Cache expensive deterministic work.
- Prefer scene-level retries over whole-project reruns.
- Do not sacrifice correctness for unmeasured optimization.

## Performance Tests

Maintain benchmarks for:

- LLM planning
- image generation
- video generation
- TTS
- FFmpeg render
- project load/resume

## Regression Thresholds

Where practical, define acceptable regression thresholds instead of relying on subjective speed claims.

## Memory Safety

Before heavyweight generation:

1. Check available memory.
2. Estimate workload/provider requirements when possible.
3. Refuse or downgrade unsafe configurations.
4. Give the user a clear reason and fallback.
