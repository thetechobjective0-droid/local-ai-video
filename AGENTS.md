# AGENTS.md — Local AI Video

## Purpose

This file defines how AI coding agents must work in the `local-ai-video` repository.

The repository is a local-only AI video generation platform for Apple Silicon. Agents must optimize for correctness, inspectability, reproducibility, maintainability, and measured performance on the target M4/36 GB machine.

## Mission

Build the smallest reliable end-to-end local video pipeline first, then expand capabilities without unnecessary architectural complexity.

## Non-Negotiable Local-Only Policy

- Core inference and media generation must execute locally.
- No cloud LLM, image, video, TTS, or music inference in the core path.
- No automatic upload of prompts, source media, generated artifacts, logs, or telemetry.
- Internet access is permitted only for explicit installation, dependency updates, model downloads, documentation lookup, or source-control operations.
- Agents must never add a remote inference dependency without an explicit architectural decision.

## Core Principles

1. **Local-only:** inference and processing stay on the user's machine.
2. **Provider-agnostic:** model-specific code stays behind provider interfaces.
3. **Artifact-first:** every stage produces inspectable artifacts and metadata.
4. **Resumable:** failed stages can be rerun independently.
5. **Deterministic where possible:** persist seeds, prompts, configuration, hashes, and versions.
6. **Bounded autonomy:** agent loops have explicit retry and time budgets.
7. **Validate at boundaries:** never trust raw model/provider output.
8. **Simple before sophisticated:** introduce complexity only when justified.
9. **Measure before optimizing:** benchmark the actual M4/36 GB target.
10. **Documentation is a deliverable:** implementation, tests, docs, configuration, and operational guidance move together.
11. **No generated binaries in Git:** generated media belongs under ignored local data directories.

## Agent Roles

### Architect Agent
Maintain architecture consistency, dependency direction, provider boundaries, and alignment with `plan.md`.

### Director/Prompt Agent
Design versioned prompts and structured creative briefs, scripts, storyboards, and generation prompts.

### Implementation Agent
Implement the smallest complete vertical slice, follow conventions, add tests, and avoid unrelated refactoring.

### Provider Agent
Integrate local LLM/image/video/TTS/music backends behind interfaces, including health checks, capabilities, and metadata.

### QA/Test Agent
Build unit, contract, integration, regression, and end-to-end tests, including negative/error paths.

### Performance Agent
Measure generation time, memory, disk, and concurrency; recommend optimization only after baselines exist.

### Security Agent
Review filesystem boundaries, subprocess execution, path traversal, secrets, dependency risks, and malicious media/model output.

### Documentation Agent
Maintain README, architecture docs, ADRs, configuration references, CLI/API documentation, troubleshooting guides, phase documentation, examples, and migration notes. Documentation must remain synchronized with implementation.

### Reviewer Agent
Review correctness, tests, maintainability, security, performance, documentation, and consistency with the project plan.

## Agent Workflow

Before modifying code:

1. Read `plan.md` and relevant documentation.
2. Read the applicable skill under `.agents/skills/`.
3. Identify the current phase and milestone.
4. Inspect existing code and tests.
5. Determine the smallest change that advances the milestone.
6. Identify documentation that must change.

While coding:

1. Make focused changes.
2. Reuse existing abstractions.
3. Keep provider-specific logic behind adapters.
4. Validate all external/model boundaries.
5. Add/update tests in the same change.
6. Update relevant documentation in the same change.
7. Avoid unrelated formatting/refactoring.

Before finishing:

1. Run formatter/linter.
2. Run unit tests.
3. Run relevant integration/contract tests.
4. Run type checks when configured.
5. Run an E2E smoke test when practical.
6. Review the diff.
7. Update documentation and examples.
8. Record hardware-only validation that could not run in CI.

## Skills

Reusable engineering skills live under `.agents/skills/`. A skill is an executable development playbook, not merely background advice. Agents should read the relevant skill before performing the associated task.

Every feature should use the appropriate combination of coding, testing, provider-integration, security, performance, debugging, review, and documentation skills.

## Coding Rules

### Python

- Use type hints for public interfaces and non-trivial functions.
- Prefer Pydantic models at application boundaries.
- Use `pathlib.Path` for filesystem paths.
- Avoid mutable global state.
- Raise domain-specific exceptions.
- Keep functions small and focused.
- Prefer dependency injection over hard-coded provider construction.
- Never use `eval` or `exec` for user/model output.
- Never interpolate untrusted strings into shell commands.
- Use subprocess argument arrays and explicit timeouts.

### API

Validate request/response schemas. Keep provider details out of route handlers. Return actionable errors without secrets.

### Configuration

No hard-coded secrets, usernames, absolute machine paths, or API credentials. Provide safe defaults and documented configuration examples.

### Logging

Include project ID, run ID, stage, scene ID where relevant, provider, model, duration, and status. Never log secrets.

## Provider Interface Rules

Every provider must expose normalized request/response structures, capability metadata, health/status where applicable, normalized errors, and provider/model metadata. Business logic depends on interfaces, never concrete SDKs.

## LLM Rules

LLM output is untrusted input:

```text
LLM output -> parse -> validate -> repair/retry if allowed -> persist
```

LLM output must never directly execute shell commands, Python, SQL, arbitrary filesystem operations, or network requests. Deterministic application code validates and executes approved actions.

## Prompt Rules

- Prompts live in versioned files.
- Every prompt has a version identifier.
- Store prompt version with generation metadata.
- Keep system instructions separate from variable project data.
- Prefer structured output.
- Maintain golden fixtures for important prompts.

## Testing Requirements

Every feature requires tests at the appropriate layer.

### Unit
Schema validation, state transitions, duration/timeline calculations, provider selection, cache keys, retry policy, hashing, configuration.

### Contract
Every provider adapter proves conformance using fake/mock backends where possible.

### Integration
Stage-to-stage behavior without requiring heavyweight models in normal CI.

### E2E
Maintain a lightweight deterministic fixture pipeline. Hardware/model tests are separately tagged and run on the M4 machine.

### Test naming

Use behavioral names such as:

```text
test_invalid_storyboard_duration_is_rejected
test_failed_image_generation_can_be_retried
test_cached_generation_is_invalidated_when_seed_changes
```

## Documentation Requirements

Documentation is part of the Definition of Done. For every meaningful feature, provide the applicable:

- purpose and scope
- architecture/data flow
- interfaces and schemas
- setup/configuration
- CLI/API usage
- inputs/outputs
- failure modes and recovery
- test instructions and coverage
- M4/36 GB resource considerations
- security considerations
- provider/model/prompt versions
- troubleshooting
- migration/change notes
- runnable examples

See `docs/DOCUMENTATION_STANDARD.md` for the full documentation contract.

## File and Artifact Rules

Use `data/projects/<project-id>/` for generated project data. Every artifact should record creator, provider/model, inputs, parameters, timestamp, and relevant hashes. Generated media, model weights, and caches must never be committed to Git.

## Performance Rules

Heavy media generation defaults to concurrency 1 until measurements justify more. Record LLM, image, video, TTS, render latency, peak memory, disk usage, and output size.

## Failure Handling

Classify failures as transient, configuration, provider unavailable, invalid model output, resource exhaustion, validation failure, or permanent. Retries are bounded and only allowed for explicitly retryable failures.

## Security Rules

- Never pass user/LLM strings through a shell.
- Resolve and validate project paths.
- Reject path traversal.
- Limit subprocess runtime.
- Sanitize user-controlled filenames.
- Keep secrets out of logs and Git.
- Validate external media before processing.

## Definition of Done

A change is complete only when implementation, tests, documentation, configuration/examples, error behavior, and relevant validation are consistent and the diff contains no generated artifacts or secrets.

## Git Rules

Use clear scoped commits such as:

```text
feat: add storyboard validation
fix: recover failed scene generation
test: add render-plan validation
docs: update local setup
```

Do not commit model weights, generated media, secret-bearing `.env` files, caches, or IDE state.

## Review Gates

Core architecture changes require review for correctness, tests, provider isolation, errors, resource safety, security, compatibility, and documentation. Provider changes additionally require licensing, model availability, hardware, memory, and fallback review.

## What Agents Must Not Do

- Do not silently introduce cloud inference.
- Do not hard-code model names into unrelated modules.
- Do not create unbounded autonomous loops.
- Do not hide failures as success.
- Do not skip tests.
- Do not commit generated media.
- Do not rewrite working modules merely for style.
- Do not change architecture without documenting the decision.
