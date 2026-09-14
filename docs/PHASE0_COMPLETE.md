# Phase 0 — Foundation Status

## Implemented

- Python package foundation with Pydantic and Typer.
- Local-only validated YAML configuration.
- Fast/Balanced/Quality runtime profile validation.
- Structured logging with project/run/stage correlation context.
- Domain-specific exceptions for provider, disk, and memory failures.
- Safe filesystem project store with path containment checks.
- Project JSON persistence and validated round-trip loading.
- Disk-space safety preflight.
- Physical memory and disk resource snapshot.
- Apple Silicon detection.
- Python runtime detection.
- FFmpeg executable detection.
- Ollama HTTP reachability and local-model count check.
- CLI `health` and `doctor` commands with optional `--config`.
- Unit coverage for configuration, health, Ollama, filesystem, and resource preflight.
- Generated media/cache/model ignore rules remain enforced by `.gitignore`.

## Validation on the developer M4

Run:

```bash
uv sync --extra dev
uv run ruff format --check .
uv run ruff check .
uv run mypy app
uv run pytest
uv run video-agent doctor
```

`doctor` is intentionally a live environment check. It should pass only when the target machine has FFmpeg and a reachable local Ollama service.

## Completion gate

Phase 0 is considered complete after the commands above pass on the target M4/36 GB machine. Heavy media model validation is deliberately deferred to later phases.
