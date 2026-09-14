.PHONY: install test lint format-check typecheck check doctor

install:
	uv sync --extra dev

test:
	uv run pytest

lint:
	uv run ruff check .

format-check:
	uv run ruff format --check .

typecheck:
	uv run mypy app

check: format-check lint typecheck test

doctor:
	uv run video-agent doctor
