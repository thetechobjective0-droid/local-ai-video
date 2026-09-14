# AGENTS.md — Local AI Video

## Purpose

This file defines how AI coding agents must work in the `local-ai-video` repository.

The repository is a local-first AI video generation platform for Apple Silicon. Agents must optimize for correctness, inspectability, reproducibility, maintainability, and measured performance on the target M4/36 GB machine.

## Mission

Build the smallest reliable end-to-end local video pipeline first, then expand capabilities without creating unnecessary architectural complexity.

## Core Principles

1. **Local-first:** core generation must work without paid cloud inference.
2. **Provider-agnostic:** do not spread model-specific code through application logic.
3. **Artifact-first:** each stage produces inspectable artifacts and metadata.
4. **Resumable:** failed stages must be rerunnable independently.
5. **Deterministic where possible:** persist seeds, prompts, model/configuration, hashes, and versions.
6. **Bounded autonomy:** agent loops have explicit retry and time budgets.
7. **Validate at boundaries:** never trust raw model/provider output.
8. **Simple before sophisticated:** do not introduce agents, queues, databases, or services before their need is demonstrated.
9. **Measure before optimizing:** collect baseline timing and memory data on the actual M4 hardware.
10. **No generated binaries in Git:** generated media belongs under local data directories excluded from source control.

## Agent Roles

### Architect Agent

Responsibilities:

- Maintain architecture consistency.
- Review dependency direction and provider boundaries.
- Reject unnecessary coupling and premature abstraction.
- Keep the implementation aligned with `plan.md`.

### Director/Prompt Agent

Responsibilities:

- Design and maintain versioned prompts.
- Generate structured creative briefs, scripts, storyboards, and generation prompts.
- Prefer deterministic templates and schemas over free-form outputs.

### Implementation Agent

Responsibilities:

- Implement the smallest complete vertical slice.
- Follow repository conventions.
- Add tests with code changes.
- Avoid unrelated refactoring.

### Provider Agent

Responsibilities:

- Integrate LLM, image, video, TTS, or music backends behind interfaces.
- Persist provider/model configuration and generation metadata.
- Implement health checks and capability metadata.

### QA/Test Agent

Responsibilities:

- Build and maintain unit, integration, contract, regression, and end-to-end tests.
- Add negative/error-path tests.
- Verify artifact integrity and deterministic behavior where expected.

### Performance Agent

Responsibilities:

- Measure generation time, memory pressure, disk usage, and concurrency behavior.
- Recommend optimization only after a baseline exists.
- Protect the M4/36 GB target from unsafe defaults.

### Security Agent

Responsibilities:

- Review filesystem handling, subprocess execution, shell escaping, path traversal, secrets, and dependency risks.
- Ensure user-generated content cannot escape project boundaries.

### Reviewer Agent

Responsibilities:

- Review changes for correctness, tests, maintainability, security, and consistency with the project plan.
- Prefer concrete actionable feedback.

## Agent Workflow

Before modifying code:

1. Read `plan.md` and relevant package documentation.
2. Identify the current phase and milestone.
3. Inspect existing code and tests.
4. Determine the smallest change that advances the milestone.
5. State assumptions in the implementation notes when they materially affect behavior.

While coding:

1. Make focused changes.
2. Reuse existing abstractions before creating new ones.
3. Keep provider-specific logic behind provider adapters.
4. Add validation at external boundaries.
5. Add or update tests in the same change.
6. Avoid drive-by formatting or unrelated refactors.

Before finishing:

1. Run formatter/linter.
2. Run unit tests.
3. Run relevant integration/contract tests.
4. Run type checks if configured.
5. Run an end-to-end smoke test when the affected path permits it.
6. Review the diff for accidental changes.
7. Update documentation/configuration examples when behavior changes.
8. Record any hardware-only validation that could not run in CI.

## Change Size Rules

Prefer changes that are:

- Small enough to review.
- Independently testable.
- Reversible.
- Tied to one milestone or one defect.

Avoid combining:

- New provider integration + large refactor.
- UI redesign + backend architecture changes.
- Dependency upgrades + unrelated feature work.

## Coding Rules

### Python

- Use type hints for public interfaces and non-trivial internal functions.
- Prefer Pydantic models for external/application boundaries.
- Use `pathlib.Path` for filesystem paths.
- Avoid mutable global state.
- Raise domain-specific exceptions.
- Keep functions small and single-purpose.
- Prefer dependency injection over hard-coded provider construction.
- Never use `eval` or `exec` for user/model output.
- Do not construct shell commands by string interpolation.
- Use `subprocess.run([...])` argument arrays with explicit timeouts.

### API

- Validate request/response schemas.
- Keep provider implementation details out of route handlers.
- Return actionable error responses without exposing secrets or raw credentials.

### Configuration

- No hard-coded API keys, absolute local paths, usernames, or machine-specific secrets.
- Use environment variables/config files.
- Provide `.env.example` or documented configuration defaults.

### Logging

Log:

- project id
- run id
- stage
- scene id where relevant
- provider
- model
- duration
- status

Do not log secrets or unnecessary sensitive user content.

## Dependency Rules

Use dependencies only when they provide clear value.

Preferred categories:

- Pydantic for schemas.
- Typer for CLI.
- FastAPI only when API phase begins.
- Pytest for tests.
- Ruff for lint/format.
- FFmpeg for rendering.
- Ollama for initial local LLM serving.

Do not add a heavy framework to solve a problem that can be solved with the standard library.

## Provider Interface Rules

Every media/LLM provider must expose:

- capability information
- health/status where applicable
- generation method
- normalized request/response structures
- error normalization
- provider/model metadata

Business logic must depend on provider interfaces, not concrete SDKs.

## LLM Rules

LLM output is untrusted input.

Required flow:

```text
LLM output -> parse -> validate -> repair/retry if necessary -> persist
```

Do not let arbitrary LLM output directly execute:

- shell commands
- Python code
- SQL
- filesystem paths outside the project boundary
- network requests

When an LLM proposes an action, deterministic application code must validate and execute it.

## Prompt Rules

- Prompts live in versioned files, not giant inline Python strings.
- Every prompt has a version identifier.
- Store prompt version with generation metadata.
- Keep system instructions separate from variable project data.
- Use structured output whenever possible.
- Test important prompts with fixed fixtures.

## File and Artifact Rules

Project-local data should follow:

```text
data/projects/<project-id>/
```

Generated artifacts should never be committed to Git.

Every generated artifact should have enough metadata to answer:

- what created it
- with which provider/model
- using which inputs
- with which parameters
- when it was created

## Testing Requirements

Every new feature requires at least one test at the appropriate layer.

### Unit tests

Must cover:

- schema validation
- state transitions
- duration/timeline calculations
- provider selection
- cache keys
- retry policies
- artifact hashing
- configuration behavior

### Contract tests

Each provider adapter must prove it conforms to the provider interface using fake/mock backends where possible.

### Integration tests

Cover stage-to-stage behavior without requiring large models in ordinary CI.

### End-to-end tests

Maintain at least one lightweight deterministic fixture pipeline.

Hardware-dependent model tests should be separately tagged and run on the M4 machine.

## Test Naming

Use names that describe behavior, for example:

```text
test_invalid_storyboard_duration_is_rejected

test_failed_image_generation_can_be_retried

test_cached_generation_is_invalidated_when_seed_changes
```

## Definition of Done

A change is not done until:

- implementation is complete
- tests are added/updated
- relevant checks pass
- documentation/config examples are updated if necessary
- no generated artifacts or secrets are committed
- error behavior is intentional
- the diff is focused

## Git Rules

Commit messages should be clear and scoped.

Preferred style:

```text
feat: add storyboard validation
fix: recover failed scene generation
refactor: isolate ollama provider
 test: add render-plan validation
 docs: update local setup
```

Do not commit:

- model weights
- generated images/video/audio
- `.env` files containing secrets
- local IDE state
- cache directories
- machine-specific temporary files

## Review Gates

A change touching core architecture should be reviewed for:

1. Correctness
2. Test coverage
3. Provider isolation
4. Error handling
5. Resource safety
6. Security
7. Backward compatibility
8. Documentation

A provider integration should additionally be checked for:

- licensing assumptions
- model availability
- hardware requirements
- memory behavior
- fallback behavior

## Performance Rules

Do not increase concurrency merely because multiple jobs are logically independent.

For heavyweight media generation, default concurrency is one until measurements prove otherwise.

Record benchmarks for:

- LLM planning latency
- image generation latency
- video generation latency
- TTS latency
- render latency
- peak memory
- output size

## Failure Handling

Failures must be classified as:

- transient
- configuration
- provider unavailable
- invalid model output
- resource exhaustion
- validation failure
- permanent

Retries are permitted only for explicitly retryable failures and must be bounded.

## Security Rules

- Never pass user/LLM strings through a shell.
- Resolve and validate all project paths.
- Reject path traversal such as `../` escapes.
- Limit subprocess runtime.
- Sanitize uploaded/user-controlled filenames.
- Keep secrets out of logs and Git.
- Validate external files before processing.

## Documentation Rules

When behavior changes, update the relevant documentation in the same change.

At minimum consider:

- README
- plan.md
- configuration examples
- provider docs
- CLI help
- API schemas

## What Agents Must Not Do

- Do not silently change architecture because a single provider is inconvenient.
- Do not hard-code a model name into unrelated modules.
- Do not create an unbounded autonomous loop.
- Do not hide failures by returning fake success.
- Do not skip tests because a change appears small.
- Do not commit generated media.
- Do not add cloud dependencies to the core path without an explicit architectural decision.
- Do not rewrite working modules just for stylistic preference.

## Escalation

When an implementation choice materially affects architecture, resource usage, provider compatibility, or data model stability, document the decision in the relevant design documentation before proceeding.
