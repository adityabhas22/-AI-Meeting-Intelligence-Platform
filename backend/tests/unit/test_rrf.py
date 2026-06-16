from app.retrieval.rrf import reciprocal_rank_fusion


def test_item_ranked_in_both_lists_beats_items_in_one():
    semantic = ["a", "b", "c"]
    keyword = ["b", "a", "d"]
    fused = reciprocal_rank_fusion([semantic, keyword], k=60)
    ids = [item for item, _ in fused]
    assert set(ids[:2]) == {"a", "b"}  # present in both, so they win
    assert ids[-1] in {"c", "d"}  # present in only one


def test_single_list_preserves_order():
    fused = reciprocal_rank_fusion([["x", "y", "z"]])
    assert [item for item, _ in fused] == ["x", "y", "z"]


def test_higher_rank_scores_higher():
    fused = dict(reciprocal_rank_fusion([["first", "second"]], k=60))
    assert fused["first"] > fused["second"]


def test_empty_inputs():
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[], []]) == []
