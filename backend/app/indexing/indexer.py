"""Chunk a meeting's transcript, embed each chunk, and persist the rows. The embed
step is injectable (a callable taking texts and returning vectors) so tests run with
deterministic fake vectors and no API cost."""

import uuid
from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.indexing.chunker import Chunk, chunk_segments
from app.indexing.embeddings import embed_texts
from app.models import TranscriptChunk
from app.transcription.models import TranscriptSegment

Embedder = Callable[[list[str]], list[list[float]]]


async def persist_chunks(
    session: AsyncSession,
    meeting_id: uuid.UUID,
    chunks: list[Chunk],
    vectors: list[list[float]],
) -> list[TranscriptChunk]:
    rows = [
        TranscriptChunk(
            meeting_id=meeting_id,
            idx=chunk.idx,
            text=chunk.text,
            start_sec=chunk.start_sec,
            end_sec=chunk.end_sec,
            embedding=vector,
        )
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]
    session.add_all(rows)
    await session.flush()
    return rows


async def index_meeting(
    session: AsyncSession,
    meeting_id: uuid.UUID,
    segments: list[TranscriptSegment],
    *,
    embed: Embedder | None = None,
) -> list[TranscriptChunk]:
    chunks = chunk_segments(segments)
    if not chunks:
        return []
    embed = embed or embed_texts
    vectors = embed([c.text for c in chunks])
    return await persist_chunks(session, meeting_id, chunks, vectors)
