"""Project-level QA that identifies the exact invalid scene or artifact."""

import json
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from app.exceptions import VideoAgentError
from app.models.artifact import Artifact
from app.models.project import VideoProject
from app.models.scene import Scene
from app.models.timeline import Timeline
from app.qa.audio_quality import validate_audio_quality
from app.qa.media import validate_audio, validate_image
from app.render.validator import validate_video
from app.storage.filesystem import FilesystemStore


@dataclass(frozen=True)
class QAFailure:
    """One actionable QA failure tied to a scene or project artifact."""

    scope: str
    message: str


@dataclass(frozen=True)
class QAReport:
    """Deterministic project QA result."""

    passed: bool
    failures: tuple[QAFailure, ...]


def validate_project(
    store: FilesystemStore,
    project_id: UUID,
    *,
    ffprobe_command: str = "ffprobe",
    ffmpeg_command: str = "ffmpeg",
) -> QAReport:
    """Validate project assets, timeline, subtitles, and final video when present."""
    failures: list[QAFailure] = []
    directory = store.project_dir(project_id)
    try:
        project = store.load_project(project_id)
    except Exception as exc:
        return QAReport(False, (QAFailure("project", f"project.json is invalid: {exc}"),))

    scenes = _load_scenes(directory, failures)
    if not scenes:
        failures.append(QAFailure("project", "no valid scene manifests found"))

    for scene in scenes:
        _validate_scene_assets(directory, project, scene, failures, ffprobe_command, ffmpeg_command)

    timeline_path = directory / "timeline.json"
    timeline = _load_timeline(timeline_path, failures)
    if timeline is not None:
        _validate_timeline(project, scenes, timeline, failures)
    else:
        failures.append(QAFailure("timeline", "timeline.json is missing or invalid"))

    _validate_subtitles(directory, timeline, failures)

    final_video = directory / "final.mp4"
    if final_video.exists():
        try:
            validate_video(
                final_video,
                expected_duration=project.duration_seconds,
                expected_fps=timeline.fps if timeline else project.fps,
                expected_resolution=timeline.resolution if timeline else project.resolution,
                ffprobe_command=ffprobe_command,
            )
        except (VideoAgentError, ValueError) as exc:
            failures.append(QAFailure("final-video", str(exc)))

    return QAReport(not failures, tuple(failures))


def _load_scenes(directory: Path, failures: list[QAFailure]) -> list[Scene]:
    scenes: list[Scene] = []
    for path in sorted(directory.glob("scene-*.json")):
        if path.name.endswith(("-image.json", "-audio.json", "-video.json")):
            continue
        try:
            scenes.append(Scene.model_validate_json(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            failures.append(QAFailure(path.name, f"invalid scene manifest: {exc}"))
    return sorted(scenes, key=lambda scene: scene.index)


def _load_timeline(path: Path, failures: list[QAFailure]) -> Timeline | None:
    if not path.is_file():
        return None
    try:
        return Timeline.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(QAFailure("timeline", f"invalid timeline manifest: {exc}"))
        return None


def _load_artifact(directory: Path, filename: str, failures: list[QAFailure]) -> Artifact | None:
    path = directory / filename
    if not path.is_file():
        failures.append(QAFailure(filename, "artifact manifest is missing"))
        return None
    try:
        return Artifact.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(QAFailure(filename, f"invalid artifact manifest: {exc}"))
        return None


def _validate_scene_assets(
    directory: Path,
    project: VideoProject,
    scene: Scene,
    failures: list[QAFailure],
    ffprobe_command: str,
    ffmpeg_command: str,
) -> None:
    scope = f"scene-{scene.index:04d}"
    if scene.image_asset is not None:
        artifact = _load_artifact(directory, f"scene-{scene.index:04d}-image.json", failures)
        if artifact is not None:
            if artifact.id != scene.image_asset:
                failures.append(QAFailure(scope, "image asset UUID does not match scene manifest"))
            try:
                validate_image(artifact.path, expected_width=None, expected_height=None)
            except VideoAgentError as exc:
                failures.append(QAFailure(scope, f"image QA failed: {exc}"))
    if scene.audio_asset is not None:
        artifact = _load_artifact(directory, f"scene-{scene.index:04d}-audio.json", failures)
        if artifact is not None:
            if artifact.id != scene.audio_asset:
                failures.append(QAFailure(scope, "audio asset UUID does not match scene manifest"))
            try:
                validate_audio(artifact.path, expected_duration=scene.duration_seconds, ffprobe_command=ffprobe_command)
                quality = validate_audio_quality(artifact.path, ffmpeg_command=ffmpeg_command)
                artifact.parameters["qa_audio_quality"] = quality
            except (VideoAgentError, ValueError) as exc:
                failures.append(QAFailure(scope, f"audio quality QA failed: {exc}"))
    if scene.video_asset is not None:
        artifact = _load_artifact(directory, f"scene-{scene.index:04d}-video.json", failures)
        if artifact is not None:
            if artifact.id != scene.video_asset:
                failures.append(QAFailure(scope, "video asset UUID does not match scene manifest"))
            try:
                validate_video(
                    artifact.path,
                    expected_duration=scene.duration_seconds,
                    expected_fps=int(artifact.parameters.get("fps", project.fps)),
                    expected_resolution=f"{artifact.parameters.get('width')}x{artifact.parameters.get('height')}",
                    require_audio=False,
                    ffprobe_command=ffprobe_command,
                )
            except (VideoAgentError, ValueError) as exc:
                failures.append(QAFailure(scope, f"video QA failed: {exc}"))


def _validate_timeline(project: VideoProject, scenes: list[Scene], timeline: Timeline, failures: list[QAFailure]) -> None:
    if timeline.project_id != project.id:
        failures.append(QAFailure("timeline", "timeline project UUID does not match project"))
    if abs(timeline.duration_seconds - project.duration_seconds) > 0.05:
        failures.append(QAFailure("timeline", "timeline duration does not match project duration"))
    cursor = 0.0
    for item in sorted(timeline.scenes, key=lambda scene: scene.index):
        if abs(item.start_seconds - cursor) > 1e-6:
            failures.append(QAFailure(f"scene-{item.index:04d}", "timeline contains a timing gap or overlap"))
        if item.duration_seconds <= 0:
            failures.append(QAFailure(f"scene-{item.index:04d}", "timeline duration is not positive"))
        cursor += item.duration_seconds
    if abs(cursor - timeline.duration_seconds) > 0.05:
        failures.append(QAFailure("timeline", "timeline scene durations do not sum to timeline duration"))
    scene_ids = {scene.id for scene in scenes}
    timeline_ids = {scene.scene_id for scene in timeline.scenes}
    missing = scene_ids - timeline_ids
    if missing:
        failures.append(QAFailure("timeline", f"scenes missing from timeline: {sorted(map(str, missing))}"))


def _validate_subtitles(directory: Path, timeline: Timeline | None, failures: list[QAFailure]) -> None:
    if timeline is None:
        return
    path = directory / ("subtitles.vtt" if timeline.subtitle_format == "vtt" else "subtitles.srt")
    if not path.is_file() or path.stat().st_size == 0:
        failures.append(QAFailure("subtitles", f"subtitle file is missing or empty: {path.name}"))
