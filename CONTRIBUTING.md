# Contributing and Coding Standards

## Development Flow

```text
Issue / requirement
      ↓
Inspect plan + architecture
      ↓
Create focused implementation
      ↓
Add tests
      ↓
Run local checks
      ↓
Review diff
      ↓
Commit / PR
```

## Before Coding

- Identify the relevant phase in `plan.md`.
- Read `AGENTS.md`.
- Read applicable `.agents/skills/*`.
- Inspect existing interfaces and tests.
- Confirm the change does not duplicate an existing abstraction.

## While Coding

- Keep changes focused.
- Prefer explicit code over clever code.
- Keep provider-specific behavior behind interfaces.
- Validate inputs at module boundaries.
- Use clear names.
- Avoid speculative features.
- Add tests at the same time as implementation.

## Before Commit

Run the project checks configured in `pyproject.toml`.

Recommended baseline:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

Run additional integration or hardware checks relevant to the change.

## Commit Messages

Use a conventional scope where practical:

```text
feat: add storyboard planner
fix: reject overlapping scenes
refactor: isolate provider registry
test: add cache invalidation tests
docs: document local setup
perf: reduce render memory usage
```

## Pull Requests

PRs should explain:

- Problem
- Approach
- Key files changed
- Tests
- Hardware validation
- Performance impact
- Risks
- Follow-up work

## Generated Files

Never commit:

- model weights
- model caches
- generated videos
- generated images
- generated audio
- local databases
- `.env`
- secrets
- IDE/system files

## Review Standard

A PR should leave the codebase easier to understand and operate than before. Avoid unrelated formatting, dependency, or architecture changes.
