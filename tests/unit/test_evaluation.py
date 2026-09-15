from app.evaluation import _jaccard, _scene_text, _tokens
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
