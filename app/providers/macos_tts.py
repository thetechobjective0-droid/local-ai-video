"""Local macOS text-to-speech provider using the built-in `say` command."""

import hashlib
import subprocess
import wave
from pathlib import Path

from app.exceptions import ProviderUnavailableError, VideoAgentError
from app.providers.tts import TTSRequest, TTSResult


class MacOSTTSProvider:
    """Synthesize narration entirely on-device through macOS Speech."""

    provider_name = "macos_say"

    def __init__(self, *, command: str = "say", sample_rate: int = 22050) -> None:
        self.command = command
        self.sample_rate = sample_rate

    def _ensure_available(self) -> None:
        try:
            subprocess.run(
                [self.command, "--version"],
                check=False,
                capture_output=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ProviderUnavailableError("macOS say command is unavailable") from exc

    def synthesize(self, request: TTSRequest) -> TTSResult:
        if not request.text.strip():
            raise ValueError("TTS text must not be empty")
        if request.rate <= 0:
            raise ValueError("TTS rate must be positive")
        self._ensure_available()
        output = request.output_path
        output.parent.mkdir(parents=True, exist_ok=True)
        command = [
            self.command,
            "-o",
            str(output),
            "--data-format",
            f"LEI16@{self.sample_rate}",
            "--rate",
            str(request.rate),
        ]
        if request.voice:
            command.extend(["--voice", request.voice])
        command.append(request.text)
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired as exc:
            raise ProviderUnavailableError("macOS TTS synthesis timed out") from exc
        except OSError as exc:
            raise ProviderUnavailableError("macOS TTS synthesis could not start") from exc
        if completed.returncode != 0:
            detail = completed.stderr.strip() or "unknown macOS TTS error"
            raise VideoAgentError(f"macOS TTS synthesis failed: {detail}")
        if not output.is_file() or output.stat().st_size == 0:
            raise VideoAgentError("macOS TTS returned no usable audio file")
        duration, sample_rate, channels = _read_wave_info(output)
        digest = hashlib.sha256(output.read_bytes()).hexdigest()
        return TTSResult(
            path=output,
            provider=self.provider_name,
            model="macos-speech",
            voice=request.voice,
            duration_seconds=duration,
            sample_rate=sample_rate,
            channels=channels,
            sha256=digest,
            metadata=request.metadata,
        )


def _read_wave_info(path: Path) -> tuple[float, int, int]:
    try:
        with wave.open(str(path), "rb") as audio:
            frames = audio.getnframes()
            sample_rate = audio.getframerate()
            channels = audio.getnchannels()
            sample_width = audio.getsampwidth()
            payload = audio.readframes(frames)
    except (wave.Error, OSError) as exc:
        raise VideoAgentError("TTS provider returned an invalid WAV file") from exc
    if sample_rate <= 0 or channels <= 0 or frames <= 0 or sample_width <= 0:
        raise VideoAgentError("TTS provider returned an empty WAV file")
    if not payload or not any(payload):
        raise VideoAgentError("macOS TTS returned entirely silent audio")
    return frames / sample_rate, sample_rate, channels
