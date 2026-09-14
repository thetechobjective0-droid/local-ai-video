# Debugging Skill

## Procedure

1. Reproduce the failure.
2. Capture exact error/log context.
3. Identify the failing stage and artifact.
4. Minimize the failing input.
5. Determine whether the failure is deterministic.
6. Fix the root cause, not only the symptom.
7. Add a regression test.
8. Re-run the affected test matrix.

## AI/Generation Debugging

Record:

- project id
- scene id
- provider/model
- prompt version
- generation parameters
- seed
- input artifact hashes
- output validation result

Do not blindly regenerate repeatedly. Inspect the failure class first.

## Common Classes

- Schema failure
- Provider unavailable
- Model unavailable
- Resource exhaustion
- Invalid output
- Render failure
- Filesystem error
- Timing mismatch
- Cache inconsistency

## Completion Rule

A debugging task is incomplete without a reproducible regression test when the defect is testable in software.
