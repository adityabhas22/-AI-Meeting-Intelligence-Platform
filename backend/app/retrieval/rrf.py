"""Reciprocal Rank Fusion. Combines several ranked lists into one without needing to
normalize scores across different scales (cosine distance vs ts_rank). An item's
fused score is the sum of 1/(k + rank) across the lists it appears in. Pure."""

from collections.abc import Hashable, Sequence
from typing import TypeVar

T = TypeVar("T", bound=Hashable)

RRF_K = 60


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[T]], *, k: int = RRF_K
) -> list[tuple[T, float]]:
    scores: dict[T, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
