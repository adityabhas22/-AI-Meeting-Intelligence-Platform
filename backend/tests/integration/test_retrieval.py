from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Meeting, TranscriptChunk
from app.retrieval.retriever import hybrid_search


def _unit_vector(i: int) -> list[float]:
    v = [0.0] * 1536
    v[i] = 1.0
    return v


async def _seed(session: AsyncSession) -> Meeting:
    meeting = Meeting(title="Ops sync", filename="ops.m4a")
    session.add(meeting)
    await session.flush()
    session.add_all(
        [
            TranscriptChunk(
                meeting_id=meeting.id,
                idx=0,
                text="We deployed the kubernetes cluster upgrade this morning",
                start_sec=0.0,
                end_sec=5.0,
                embedding=_unit_vector(0),
            ),
            TranscriptChunk(
                meeting_id=meeting.id,
                idx=1,
                text="We reviewed the billing dashboard revenue numbers",
                start_sec=5.0,
                end_sec=10.0,
                embedding=_unit_vector(1),
            ),
        ]
    )
    await session.commit()
    return meeting


async def test_relevant_chunk_ranks_first_when_both_signals_agree(db_session: AsyncSession):
    await _seed(db_session)
    # query vector closest to the kubernetes chunk, and keywords also match it
    results = await hybrid_search(
        db_session, "kubernetes deployment", embed=lambda _t: [_unit_vector(0)]
    )
    assert results
    assert results[0].text.startswith("We deployed the kubernetes")
    assert results[0].meeting_title == "Ops sync"
    assert results[0].score >= results[-1].score


async def test_returns_vector_hits_when_no_keyword_match(db_session: AsyncSession):
    await _seed(db_session)
    results = await hybrid_search(
        db_session, "zzz nonexistent terms", embed=lambda _t: [_unit_vector(1)]
    )
    assert results  # vector side still produces candidates
    assert results[0].text.startswith("We reviewed the billing")


async def test_empty_archive_returns_nothing(db_session: AsyncSession):
    results = await hybrid_search(db_session, "anything", embed=lambda _t: [_unit_vector(0)])
    assert results == []


async def test_archived_meeting_chunks_excluded_from_search(db_session: AsyncSession):
    from datetime import UTC, datetime

    meeting = await _seed(db_session)
    meeting.deleted_at = datetime.now(UTC)
    await db_session.commit()

    results = await hybrid_search(db_session, "kubernetes", embed=lambda _t: [_unit_vector(0)])
    assert results == []
