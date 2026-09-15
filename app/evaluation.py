"""Deterministic semantic evaluation that complements hard media QA."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
from pathlib import Path
from uuid import UUID

from app.models.scene import Scene
from app.qa.project import validate_project
from app.storage.filesystem import FilesystemStore


@dataclass(frozen=True)
class EvaluationScore:
    name: str
    score: float
    detail: str


@dataclass(frozen=True)
class EvaluationReport:
    passed: bool
    scores: tuple[EvaluationScore, ...]
    hard_qa_passed: bool
    report_version: str = "1.1"

    def to_dict(self) -> dict[str, object]:
        return {
            "report_version": self.report_version,
            "passed": self.passed,
            "hard_qa_passed": self.hard_qa_passed,
            "scores": [asdict(score) for score in self.scores],
        }


def evaluate_project(
    store: FilesystemStore, project_id: UUID, *, minimum_score: float = 0.15
) -> EvaluationReport:
    """Score deterministic textual consistency without pretending to perform visual QA."""
    qa = validate_project(store, project_id)
    if not qa.passed:
        return EvaluationReport(passed=False, scores=(), hard_qa_passed=False)
    project = store.load_project(project_id)
    scenes = _load_scenes(store, project_id)
    project_tokens = _tokens(project.source_prompt)
    scores: list[EvaluationScore] = []

    scene_texts = [_scene_text(scene) for scene in scenes]
    scene_scores = [_jaccard(project_tokens, _tokens(text)) for text in scene_texts]
    average = sum(scene_scores) / len(scene_scores) if scene_scores else 0.0
    scores.append(
        EvaluationScore(
            "prompt_alignment",
            average,
            f"mean project-prompt token overlap across {len(scenes)} scenes",
        )
    )

    continuity_values: list[float] = []
    for index in range(max(0, len(scenes) - 1)):
        previous = scenes[index]
        current = scenes[index + 1]
        previous_tokens = _tokens(previous.visual_description or previous.image_prompt)
        current_tokens = _tokens(current.visual_description or current.image_prompt)
        continuity_values.append(_jaccard(previous_tokens, current_tokens))
    continuity = sum(continuity_values) / len(continuity_values) if continuity_values else 1.0
    scores.append(
        EvaluationScore(
            "scene_continuity",
            continuity,
            f"mean lexical continuity across {max(0, len(scenes) - 1)} scene boundaries",
        )
    )

    narration_values: list[float] = []
    for scene in scenes:
        visual_tokens = _tokens(scene.visual_description or scene.image_prompt)
        narration_tokens = _tokens(scene.narration)
        if not narration_tokens:
            narration_values.append(1.0)
        else:
            narration_values.append(_jaccard(visual_tokens, narration_tokens))
    narration_alignment = sum(narration_values) / len(narration_values) if narration_values else 1.0
    scores.append(
        EvaluationScore(
            "narration_alignment",
            narration_alignment,
            f"mean visual-to-narration lexical overlap across {len(scenes)} scenes",
        )
    )

    storyboard_values: list[float] = []
    for scene in scenes:
        image_tokens = _tokens(scene.image_prompt)
        motion_tokens = _tokens(scene.motion_prompt)
        if not image_tokens or not motion_tokens:
            storyboard_values.append(1.0)
        else:
            storyboard_values.append(_jaccard(image_tokens, motion_tokens))
    storyboard_consistency = (
        sum(storyboard_values) / len(storyboard_values) if storyboard_values else 1.0
    )
    scores.append(
        EvaluationScore(
            "storyboard_consistency",
            storyboard_consistency,
            f"mean image-to-motion lexical overlap across {len(scenes)} scenes",
        )
    )

    passed = all(score.score >= minimum_score for score in scores)
    return EvaluationReport(passed=passed, scores=tuple(scores), hard_qa_passed=True)


def write_evaluation_report(
    store: FilesystemStore, project_id: UUID, report: EvaluationReport
) -> Path:
    path = store.project_dir(project_id) / "evaluation-report.json"
    path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path


def _load_scenes(store: FilesystemStore, project_id: UUID) -> list[Scene]:
    scenes: list[Scene] = []
    for path in sorted(store.project_dir(project_id).glob("scene-*.json")):
        if path.name.endswith(("-image.json", "-audio.json", "-video.json")):
            continue
        try:
            scenes.append(Scene.model_validate_json(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return sorted(scenes, key=lambda scene: scene.index)


def _scene_text(scene: Scene) -> str:
    return " ".join(
        value
        for value in (
            scene.visual_description,
            scene.image_prompt,
            scene.motion_prompt,
            scene.narration,
        )
        if value
    )


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)

