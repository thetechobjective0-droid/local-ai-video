# Review Skill

## Review Goals

Every review evaluates:

1. Correctness
2. Tests
3. Architecture
4. Security
5. Resource usage
6. Error handling
7. Documentation
8. Backward compatibility

## Review Questions

- Does the change solve the stated problem?
- Is the abstraction at the correct boundary?
- Can a provider be replaced without changing business logic?
- What happens when the provider fails?
- What happens halfway through a project?
- Can the job resume?
- Are outputs validated?
- Are retries bounded?
- Does the change work on M4/36 GB assumptions?
- Are there regression tests?
- Are docs/config examples current?

## Reject By Default

Reviewers should request changes for:

- unbounded generation loops
- hidden failures
- secrets in source
- shell injection risks
- generated artifacts in Git
- missing tests for new behavior
- provider SDK leakage into core logic
- unrelated refactors that increase risk
