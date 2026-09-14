"""Deterministic audio quality checks using local FFmpeg filters."""

import subprocess
from pathlib import Path

from app.exceptions import VideoAgentError


def validate_audio_quality(
    path: Path,
    *,
    ffmpeg_command: str = "ffmpeg",
    max_peak_db: float = -0.1,
    max_silence_seconds: float = 2.0,
    silence_threshold_db: float = -50.0,
) -> dict[str, object]:
    """Reject fully silent/clipped narration and report measured peak/silence data."""
    if not path.is_file() or path.stat().st_size == 0:
        raise VideoAgentError(f"audio artifact is missing or empty: {path}")
    if max_silence_seconds <= 0:
        raise ValueError("max_silence_seconds must be positive")
    command = [
        ffmpeg_command,
        "-v",
        "info",
        "-i",
        str(path),
        "-af",
        f"volumedetect,silencedetect=noise={silence_threshold_db}dB:d={max_silence_seconds}",
        "-f",
        "null",
        "-",
    ]
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise VideoAgentError("ffmpeg could not inspect audio quality") from exc
    diagnostics = f"{completed.stdout}\n{completed.stderr}"
    if completed.returncode != 0:
        raise VideoAgentError("audio quality analysis failed")
    peak_db = _parse_peak(diagnostics)
    silence_events = _parse_silence_events(diagnostics)
    if peak_db is None:
        raise VideoAgentError("audio quality analysis did not report a peak level")
    if peak_db > max_peak_db:
        raise VideoAgentError(f"audio peak {peak_db:.2f} dB exceeds limit {max_peak_db:.2f} dB")
    duration = _parse_duration(diagnostics)
    if duration <= 0:
        raise VideoAgentError("audio quality analysis reported non-positive duration")
    silent_duration = sum(end - start for start, end in silence_events if end >= start)
    if silent_duration >= duration:
        raise VideoAgentError("audio artifact is entirely silent")
    return {
        "peak_db": peak_db,
        "duration_seconds": duration,
        "silence_events": len(silence_events),
        "silent_duration_seconds": round(silent_duration, 3),
        "silence_threshold_db": silence_threshold_db,
    }


def _parse_peak(text: str) -> float | None:
    for line in text.splitlines():
        if "max_volume:" in line:
            value = line.split("max_volume:", 1)[1].strip().split()[0]
            try:
                return float(value)
            except ValueError:
                return None
    return None


def _parse_duration(text: str) -> float:
    marker = "Duration: "
    for line in text.splitlines():
        if marker in line:
            value = line.split(marker, 1)[1].split(",", 1)[0]
            parts = value.split(":")
            if len(parts) == 3:
                hours, minutes, seconds = parts
                return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
    return 0.0


def _parse_silence_events(text: str) -> list[tuple[float, float]]:
    starts: list[float] = []
    events: list[tuple[float, float]] = []
    for line in text.splitlines():
        if "silence_start:" in line:
            try:
                starts.append(float(line.split("silence_start:", 1)[1].strip()))
            except ValueError:
                continue
        elif "silence_end:" in line and starts:
            try:
                end = float(line.split("silence_end:", 1)[1].split("|", 1)[0].strip())
            except ValueError:
                continue
            events.append((starts.pop(0), end))
    return events
