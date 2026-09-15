from app.evaluation import EvaluationReport, EvaluationScore, _jaccard, _scene_text, _tokens
from app.models.scene import Scene


def test_tokens_normalize_and_drop_short_words() -> None:
    assert _tokens("AI agents are fast!") == {"agents", "are", "fast"}


def test_jaccard_is_symmetric() -> None:
    left = _tokens("AI agents automate work")
    right = _tokens("agents automate tasks")
    assert _jaccard(left, right) == _jaccard(right, left)


def test_jaccard_empty_sets() -> None:
    assert _jaccard(set(), set()) == 1.0
    assert _jaccard(set(), {"agent"}) == 0.0


def test_scene_text_contains_storyboard_and_narration_fields() -> None:
    scene = Scene(
        index=1,
        duration_seconds=4,
        visual_description="A robot walks through a city",
        image_prompt="robot city street",
        motion_prompt="robot walks forward",
        narration="The robot walks through the city",
    )
    text = _scene_text(scene)
    assert "robot" in text
    assert "city" in text
    assert "walks" in text


def test_refinement_proposals_are_bounded_and_sorted_by_score() -> None:
    report = EvaluationReport(
        passed=False,
        hard_qa_passed=True,
        scores=(
            EvaluationScore("prompt_alignment", 0.40, "ok"),
            EvaluationScore("narration_alignment", 0.01, "low"),
            EvaluationScore("storyboard_consistency", 0.10, "low"),
            EvaluationScore("scene_continuity", 0.05, "low"),
        ),
    )

    proposals = report.refinement_proposals(minimum_score=0.15, max_proposals=2)

    assert len(proposals) == 2
    assert [proposal.target for proposal in proposals] == ["scene_boundary", "narration"]
    assert proposals[0].priority == 1
    assert "0.050" in proposals[0].reason
