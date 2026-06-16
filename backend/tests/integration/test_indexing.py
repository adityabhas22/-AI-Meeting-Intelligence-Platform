from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.indexing.indexer import index_meeting
from app.models import Meeting, TranscriptChunk
from app.transcription.models import TranscriptSegment


async def test_index_meeting_persists_chunks_with_embeddings_and_tsvector(db_session: AsyncSession):
    meeting = Meeting(title="Infra sync", filename="infra.m4a")
    db_session.add(meeting)
    await db_session.flush()

    segments = [
        TranscriptSegment(
            idx=i,
            speaker_label=i % 2,
            start_sec=float(i),
            end_sec=float(i + 1),
            text=f"We discussed the kubernetes migration step {i}. " * 10,
        )
        for i in range(4)
    ]
    rows = await index_meeting(
        db_session, meeting.id, segments, embed=lambda texts: [[0.1] * 1536 for _ in texts]
    )
    await db_session.commit()
    mid = meeting.id
    db_session.expunge_all()

    chunks = (
        await db_session.scalars(
            select(TranscriptChunk)
            .where(TranscriptChunk.meeting_id == mid)
            .order_by(TranscriptChunk.idx)
        )
    ).all()
    assert len(chunks) == len(rows) >= 1
    assert all(len(c.embedding) == 1536 for c in chunks)
    assert all(c.ts is not None for c in chunks)
    assert "kubernet" in chunks[0].ts


async def test_index_meeting_with_no_segments_is_noop(db_session: AsyncSession):
    meeting = Meeting(title="Empty", filename="empty.m4a")
    db_session.add(meeting)
    await db_session.flush()
    rows = await index_meeting(db_session, meeting.id, [], embed=lambda texts: [])
    assert rows == []
