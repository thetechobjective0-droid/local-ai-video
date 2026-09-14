"""Deterministic FFmpeg renderer for timeline manifests."""

import hashlib
import json
import subprocess
from pathlib import Path
from uuid import UUID

from app.exceptions import VideoAgentError
from app.models.artifact import Artifact
from app.models.timeline import Timeline
from app.recovery import RENDER_RETRY_POLICY, run_bounded
from app.render.validator import validate_video
from app.storage.filesystem import FilesystemStore


class FFmpegRenderer:
    """Render a resolved timeline through a local FFmpeg executable."""

    def __init__(self, *, command: str = "ffmpeg", ffprobe_command: str = "ffprobe") -> None:
        self.command = command
        self.ffprobe_command = ffprobe_command

    def render(self, store: FilesystemStore, project_id: UUID, timeline: Timeline) -> Artifact:
        """Render static-image/video scenes with bounded recovery."""
        directory = store.project_dir(project_id)
        if not directory.is_dir():
            raise VideoAgentError(f"project does not exist: {project_id}")
        if not timeline.scenes:
            raise VideoAgentError("cannot render an empty timeline")
        _require_contiguous_timeline(timeline)

        attempts: list[str] = []
        output = directory / timeline.output_video.name

        def operation(attempt: int) -> Artifact:
            if attempt == 0:
                attempts.append("original_render")
            else:
                attempts.append("clean_partial_output_retry")
                _remove_partial_outputs(directory, output)
            return self._render_once(store, project_id, timeline, attempts)

        try:
            result = run_bounded(operation, RENDER_RETRY_POLICY)
        except Exception as exc:
            raise VideoAgentError(f"FFmpeg render failed after bounded recovery: {exc}") from exc
        return result.value

    def _render_once(
        self,
        store: FilesystemStore,
        project_id: UUID,
        timeline: Timeline,
        recovery_strategies: list[str],
    ) -> Artifact:
        directory = store.project_dir(project_id)
        assets = _load_artifacts(directory)
        output = directory / timeline.output_video.name
        command, filter_complex = self._build_command(directory, timeline, assets, output)
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=max(300, round(timeline.duration_seconds * 20)),
            )
        except subprocess.TimeoutExpired as exc:
            raise VideoAgentError("FFmpeg render timed out") from exc
        except OSError as exc:
            raise VideoAgentError("FFmpeg executable could not be started") from exc
        if completed.returncode != 0:
            raise VideoAgentError(f"FFmpeg render failed: {completed.stderr.strip()}")

        validation = validate_video(
            output,
            expected_duration=timeline.duration_seconds,
            expected_fps=timeline.fps,
            expected_resolution=timeline.resolution,
            require_audio=True,
            ffprobe_command=self.ffprobe_command,
        )
        digest = hashlib.sha256(output.read_bytes()).hexdigest()
        artifact = Artifact(
            project_id=project_id,
            type="final_video",
            path=output,
            mime="video/mp4",
            provider="ffmpeg",
            model="h264-aac",
            sha256=digest,
            parameters={
                "duration_seconds": validation["duration_seconds"],
                "fps": timeline.fps,
                "resolution": timeline.resolution,
                "scene_count": len(timeline.scenes),
            },
        )
        store.write_json(directory, "final-video.json", artifact.model_dump(mode="json"))
        store.write_json(
            directory,
            "render.json",
            {
                "command": command,
                "filter_complex": filter_complex,
                "artifact_id": str(artifact.id),
                "recovery": {
                    "attempts": len(recovery_strategies),
                    "strategies": recovery_strategies,
                },
            },
        )
        return artifact

    def _build_command(
        self,
        directory: Path,
        timeline: Timeline,
        assets: dict[UUID, Artifact],
        output: Path,
    ) -> tuple[list[str], str]:
        width, height = _resolution(timeline.resolution)
        command = [self.command, "-y"]
        filters: list[str] = []
        concat_inputs: list[str] = []
        input_index = 0
        for scene_number, scene in enumerate(timeline.scenes):
            asset_id = scene.video_asset or scene.image_asset
            if asset_id is None:
                raise VideoAgentError(f"scene {scene.index} has no renderable image/video artifact")
            media = assets.get(asset_id)
            if media is None:
                raise VideoAgentError(f"scene {scene.index} has no renderable image/video artifact")
            media_path = _resolve_artifact_path(directory, media)
            if media.type == "scene_image":
                command.extend(
                    ["-loop", "1", "-t", _seconds(scene.duration_seconds), "-i", str(media_path)]
                )
            else:
                command.extend(["-i", str(media_path)])
            video_input = input_index
            input_index += 1

            audio = assets.get(scene.audio_asset) if scene.audio_asset else None
            if audio is not None:
                audio_path = _resolve_artifact_path(directory, audio)
                command.extend(["-i", str(audio_path)])
                audio_input = input_index
                input_index += 1
            else:
                command.extend(
                    [
                        "-f",
                        "lavfi",
                        "-t",
                        _seconds(scene.duration_seconds),
                        "-i",
                        "anullsrc=r=48000:cl=stereo",
                    ]
                )
                audio_input = input_index
                input_index += 1

            filters.append(
                f"[{video_input}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={timeline.fps},format=yuv420p,"
                f"trim=duration={_seconds(scene.duration_seconds)},setpts=PTS-STARTPTS[v{scene_number}]"
            )
            filters.append(
                f"[{audio_input}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                f"atrim=duration={_seconds(scene.duration_seconds)},asetpts=PTS-STARTPTS[a{scene_number}]"
            )
            concat_inputs.extend([f"[v{scene_number}]", f"[a{scene_number}]"])

        concat = "".join(concat_inputs)
        filters.append(f"{concat}concat=n={len(timeline.scenes)}:v=1:a=1[v][a]")
        filter_complex = ";".join(filters)
        command.extend(
            [
                "-filter_complex",
                filter_complex,
                "-map",
                "[v]",
                "-map",
                "[a]",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-r",
                str(timeline.fps),
                "-movflags",
                "+faststart",
                "-t",
                _seconds(timeline.duration_seconds),
                str(output),
            ]
        )
        return command, filter_complex


def _load_artifacts(directory: Path) -> dict[UUID, Artifact]:
    artifacts: dict[UUID, Artifact] = {}
    for path in directory.glob("*.json"):
        if path.name in {"project.json", "timeline.json", "render.json"} or path.name.startswith(
            "."
        ):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            artifact = Artifact.model_validate(payload)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        artifacts[artifact.id] = artifact
    return artifacts


def _resolve_artifact_path(directory: Path, artifact: Artifact) -> Path:
    path = artifact.path.expanduser()
    if not path.is_absolute():
        path = directory / path
    path = path.resolve()
    if not path.is_file():
        raise VideoAgentError(f"artifact file does not exist: {path}")
    return path


def _remove_partial_outputs(directory: Path, output: Path) -> None:
    """Remove only renderer-owned files before a bounded retry."""
    for path in (output, directory / "final-video.json", directory / "render.json"):
        path.unlink(missing_ok=True)


def _require_contiguous_timeline(timeline: Timeline) -> None:
    cursor = 0.0
    for scene in sorted(timeline.scenes, key=lambda item: item.index):
        if abs(scene.start_seconds - cursor) > 1e-6:
            raise VideoAgentError("Phase 6 renderer requires contiguous scene timing")
        cursor += scene.duration_seconds
    if abs(cursor - timeline.duration_seconds) > 0.05:
        raise VideoAgentError("timeline scene duration does not match project duration")


def _resolution(value: str) -> tuple[int, int]:
    try:
        width, height = value.lower().split("x", 1)
        return int(width), int(height)
    except ValueError as exc:
        raise ValueError(f"invalid resolution: {value}") from exc


def _seconds(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")
