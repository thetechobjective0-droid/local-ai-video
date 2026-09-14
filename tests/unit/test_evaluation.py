from app.evaluation import _jaccard, _tokens


def test_tokens_normalize_and_drop_short_words() -> None:
    assert _tokens("AI agents are fast!") == {"agents", "are", "fast"}


def test_jaccard_is_symmetric() -> None:
    left = _tokens("AI agents automate work")
    right = _tokens("agents automate tasks")
    assert _jaccard(left, right) == _jaccard(right, left)


def test_jaccard_empty_sets() -> None:
    assert _jaccard(set(), set()) == 1.0
    assert _jaccard(set(), {"agent"}) == 0.0
