"""Structured logging helpers for local pipeline runs."""

import logging
from contextvars import ContextVar

_project_id: ContextVar[str] = ContextVar("project_id", default="-")
_run_id: ContextVar[str] = ContextVar("run_id", default="-")
_stage: ContextVar[str] = ContextVar("stage", default="-")


class ContextFilter(logging.Filter):
    """Attach pipeline context to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.project_id = _project_id.get()
        record.run_id = _run_id.get()
        record.stage = _stage.get()
        return True


def configure_logging(level: int = logging.INFO) -> None:
    """Configure one predictable stderr handler for the application."""
    root = logging.getLogger()
    root.setLevel(level)
    if root.handlers:
        return

    handler = logging.StreamHandler()
    handler.addFilter(ContextFilter())
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s project=%(project_id)s "
            "run=%(run_id)s stage=%(stage)s %(name)s: %(message)s"
        )
    )
    root.addHandler(handler)


def set_log_context(*, project_id: str = "-", run_id: str = "-", stage: str = "-") -> None:
    """Set correlation identifiers for the current execution context."""
    _project_id.set(project_id)
    _run_id.set(run_id)
    _stage.set(stage)
