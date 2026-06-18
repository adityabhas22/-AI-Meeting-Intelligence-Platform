"""Hybrid retrieval over the archive: pgvector cosine similarity fused with Postgres
full-text search via RRF. The query embedder is injectable for tests."""

import uuid
from collections.abc import Callable

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.indexing.embeddings import embed_texts
from app.models import Meeting, TranscriptChunk
from app.retrieval.rrf import reciprocal_rank_fusion

Embedder = Callable[[list[str]], list[list[float]]]

DEFAULT_LIMIT = 5
DEFAULT_CANDIDATES = 20


class RetrievedChunk(BaseModel):
    chunk_id: uuid.UUID
    meeting_id: uuid.UUID
    meeting_title: str
    text: str
    start_sec: float
    end_sec: float
    score: float


async def hybrid_search(
    session: AsyncSession,
    query: str,
    *,
    embed: Embedder | None = None,
    limit: int = DEFAULT_LIMIT,
    candidates: int = DEFAULT_CANDIDATES,
) -> list[RetrievedChunk]:
    embed = embed or embed_texts
    query_vector = embed([query])[0]

    live = Meeting.deleted_at.is_(None)
    semantic_ids = (
        await session.scalars(
            select(TranscriptChunk.id)
            .join(Meeting, Meeting.id == TranscriptChunk.meeting_id)
            .where(live)
            .order_by(TranscriptChunk.embedding.cosine_distance(query_vector))
            .limit(candidates)
        )
    ).all()

    tsquery = func.websearch_to_tsquery("english", query)
    keyword_ids = (
        await session.scalars(
            select(TranscriptChunk.id)
            .join(Meeting, Meeting.id == TranscriptChunk.meeting_id)
            .where(TranscriptChunk.ts.bool_op("@@")(tsquery), live)
            .order_by(func.ts_rank_cd(TranscriptChunk.ts, tsquery).desc())
            .limit(candidates)
        )
    ).all()

    fused = reciprocal_rank_fusion([list(semantic_ids), list(keyword_ids)])[:limit]
    if not fused:
        return []

    score_by_id = dict(fused)
    rows = (
        await session.execute(
            select(TranscriptChunk, Meeting.title)
            .join(Meeting, Meeting.id == TranscriptChunk.meeting_id)
            .where(TranscriptChunk.id.in_(score_by_id.keys()))
        )
    ).all()

    results = [
        RetrievedChunk(
            chunk_id=chunk.id,
            meeting_id=chunk.meeting_id,
            meeting_title=title,
            text=chunk.text,
            start_sec=chunk.start_sec,
            end_sec=chunk.end_sec,
            score=score_by_id[chunk.id],
        )
        for chunk, title in rows
    ]
    results.sort(key=lambda r: r.score, reverse=True)
    return results
