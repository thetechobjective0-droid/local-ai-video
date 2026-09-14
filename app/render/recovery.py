"""Bounded recovery wrapper for final deterministic rendering."""

from pathlib import Path
from uuid import UUID

from app.exceptions import VideoAgentError
from app.models.artifact import Artifact
from app.models.timeline import Timeline
from app.recovery import RENDER_RETRY_POLICY, run_bounded
from app.render.ffmpeg import FFmpegRenderer
from app.storage.filesystem import FilesystemStore


def render_with_recovery(
    renderer: FFmpegRenderer,
    store: FilesystemStore,
    project_id: UUID,
    timeline: Timeline,
) -> tuple[Artifact, int, tuple[str, ...]]:
    """Render with one bounded retry after cleaning a partial final-output state."""
    strategies: list[str] = []
    directory = store.project_dir(project_id)
    output = directory / timeline.output_video.name

    def operation(attempt: int) -> Artifact:
        if attempt == 0:
            strategies.append("original_render")
        else:
            strategies.append("clean_partial_output_retry")
            _remove_partial_outputs(directory, output)
        return renderer.render(store, project_id, timeline)

    try:
        result = run_bounded(operation, RENDER_RETRY_POLICY)
    except Exception as exc:
        raise VideoAgentError(f"final render failed after bounded recovery: {exc}") from exc
    return result.value, result.attempts, tuple(strategies)


def _remove_partial_outputs(directory: Path, output: Path) -> None:
    """Remove only renderer-owned transient/final files before a retry."""
    for path in (output, directory / "final-video.json", directory / "render.json"):
        path.unlink(missing_ok=True)
