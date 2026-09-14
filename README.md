# Local AI Video Generator

A local-only AI video production pipeline designed for Apple Silicon, initially targeting an M4 Mac with 36 GB unified memory.

## Current status

**Phase 0 — Foundation in progress.**

The project currently contains the initial Python package, typed local-only configuration, environment health checks, CLI entry points, and Phase 0 tests.

## Local-only architecture

All inference and media processing are intended to run on the local machine:

```text
User -> CLI/UI -> Orchestrator -> Ollama/local models -> local media -> FFmpeg -> final.mp4
```

GitHub is used for source control only. The application must not automatically upload prompts, media, artifacts, logs, or telemetry.

## Development

Install with `uv`:

```bash
uv sync --extra dev
```

Run the CLI:

```bash
uv run video-agent health
uv run video-agent doctor
```

Run tests:

```bash
uv run pytest
```

Run quality checks:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

## Documentation

Read these before contributing:

- `plan.md` — implementation roadmap and architecture
- `AGENTS.md` — AI agent operating contract
- `docs/DOCUMENTATION_STANDARD.md` — documentation Definition of Done
- `.agents/skills/` — task-specific engineering playbooks
- `CONTRIBUTING.md` — contribution workflow
- `TESTING.md` — testing strategy

Documentation is a first-class deliverable. Feature changes should update the relevant docs and examples in the same change.

## Repository rule

Do not commit generated video/audio/image assets, model weights, local caches, secrets, or machine-specific state.
