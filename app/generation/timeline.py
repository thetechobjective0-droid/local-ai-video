"""Build and persist a deterministic project timeline."""

from pathlib import Path

from app.exceptions import VideoAgentError
from app.models.project import VideoProject
from app.models.scene import Scene
from app.models.timeline import Timeline, TimelineScene
from app.storage.filesystem import FilesystemStore


def build_timeline(
    store: FilesystemStore,
    project: VideoProject,
    scenes: list[Scene],
) -> Timeline:
    """Resolve scene timing/media references into a validated timeline manifest."""
    if not scenes:
        raise VideoAgentError("cannot build timeline without scenes")
    ordered = sorted(scenes, key=lambda scene: scene.index)
    previous_end = 0.0
    entries: list[TimelineScene] = []
    for scene in ordered:
        if scene.start_seconds < previous_end - 1e-6:
            raise VideoAgentError(f"scene {scene.index} overlaps the previous scene")
        end = scene.start_seconds + scene.duration_seconds
        if end > project.duration_seconds + 0.05:
            raise VideoAgentError(f"scene {scene.index} exceeds project duration")
        transition = scene.metadata.get("transition", "cut")
        if not isinstance(transition, str) or not transition.strip():
            transition = "cut"
        entries.append(
            TimelineScene(
                scene_id=scene.id,
                index=scene.index,
                start_seconds=scene.start_seconds,
                duration_seconds=scene.duration_seconds,
                narration=scene.narration,
                image_asset=scene.image_asset,
                video_asset=scene.video_asset,
                audio_asset=scene.audio_asset,
                subtitle_start_seconds=scene.start_seconds if scene.narration.strip() else None,
                subtitle_end_seconds=end if scene.narration.strip() else None,
                transition=transition,
                motion=scene.motion_prompt or None,
            )
        )
        previous_end = end

    timeline = Timeline(
        project_id=project.id,
        duration_seconds=project.duration_seconds,
        fps=project.fps,
        resolution=project.resolution,
        aspect_ratio=project.aspect_ratio,
        scenes=entries,
        metadata={"scene_count": len(entries), "output": str(Path("final.mp4"))},
    )
    store.write_json(
        store.project_dir(project.id), "timeline.json", timeline.model_dump(mode="json")
    )
    return timeline
