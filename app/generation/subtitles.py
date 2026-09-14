"""Deterministic SRT and WebVTT subtitle generation."""

import re
from pathlib import Path
from uuid import UUID

from app.exceptions import VideoAgentError
from app.models.scene import Scene
from app.storage.filesystem import FilesystemStore

_WORD_RE = re.compile(r"\S+")


def build_subtitles(
    store: FilesystemStore,
    project_id: UUID,
    scenes: list[Scene],
    *,
    max_chars: int = 48,
    formats: tuple[str, ...] = ("srt", "vtt"),
) -> dict[str, Path]:
    """Build deterministic scene-level subtitles from narration and scene timing."""
    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    requested = tuple(dict.fromkeys(formats))
    unsupported = set(requested) - {"srt", "vtt"}
    if unsupported:
        raise ValueError(f"unsupported subtitle formats: {sorted(unsupported)}")
    if not scenes:
        raise VideoAgentError("cannot generate subtitles without scenes")

    ordered = sorted(scenes, key=lambda scene: scene.index)
    _validate_scene_intervals(ordered)
    cues = _build_cues(ordered, max_chars)
    directory = store.project_dir(project_id)
    outputs: dict[str, Path] = {}
    if "srt" in requested:
        outputs["srt"] = _write(directory / "subtitles.srt", _render_srt(cues))
    if "vtt" in requested:
        outputs["vtt"] = _write(directory / "subtitles.vtt", _render_vtt(cues))
    return outputs


def _validate_scene_intervals(scenes: list[Scene]) -> None:
    previous_end = 0.0
    for scene in scenes:
        end = scene.start_seconds + scene.duration_seconds
        if scene.start_seconds < previous_end - 1e-6:
            raise VideoAgentError("scene intervals overlap; cannot build deterministic subtitles")
        previous_end = end


def _build_cues(scenes: list[Scene], max_chars: int) -> list[tuple[int, float, float, str]]:
    cues: list[tuple[int, float, float, str]] = []
    number = 1
    for scene in scenes:
        narration = " ".join(scene.narration.split())
        if not narration:
            continue
        lines = _wrap_text(narration, max_chars)
        # Scene-level narration has no word timestamps, so split its interval
        # proportionally by character count for stable, reproducible cue timing.
        weights = [max(1, len(line)) for line in lines]
        total_weight = sum(weights)
        cursor = scene.start_seconds
        for line, weight in zip(lines, weights):
            duration = scene.duration_seconds * weight / total_weight
            end = cursor + duration
            cues.append((number, cursor, end, line))
            number += 1
            cursor = end
    return cues


def _wrap_text(text: str, max_chars: int) -> list[str]:
    words = _WORD_RE.findall(text)
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if current and len(candidate) > max_chars:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _timestamp(seconds: float, *, vtt: bool = False) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    separator = "." if vtt else ","
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millis:03d}"


def _render_srt(cues: list[tuple[int, float, float, str]]) -> str:
    return "\n\n".join(
        f"{number}\n{_timestamp(start)} --> {_timestamp(end)}\n{text}"
        for number, start, end, text in cues
    ) + ("\n" if cues else "")


def _render_vtt(cues: list[tuple[int, float, float, str]]) -> str:
    body = "\n\n".join(
        f"{_timestamp(start, vtt=True)} --> {_timestamp(end, vtt=True)}\n{text}"
        for _, start, end, text in cues
    )
    return "WEBVTT\n\n" + (body + "\n" if body else "")
