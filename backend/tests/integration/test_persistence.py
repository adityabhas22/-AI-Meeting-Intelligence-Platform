from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ActionItem,
    Meeting,
    MeetingStatus,
    MeetingTopic,
    Segment,
    Speaker,
    Summary,
    TranscriptChunk,
)


async def _make_meeting(session: AsyncSession) -> Meeting:
    meeting = Meeting(title="Standup", filename="standup.m4a", duration_sec=123.4, language="en")
    meeting.speakers = [Speaker(label=0), Speaker(label=1, display_name="Bob")]
    meeting.segments = [
        Segment(idx=0, speaker_label=0, start_sec=0.0, end_sec=2.0, text="Hello everyone"),
        Segment(idx=1, speaker_label=1, start_sec=2.0, end_sec=4.0, text="Hi, I pushed the fix"),
    ]
    meeting.summary = Summary(
        overview="Quick sync",
        attendees=["Alice", "Bob"],
        key_decisions=["Ship Friday"],
        next_steps=["Bob to deploy"],
    )
    meeting.action_items = [ActionItem(idx=0, task="Deploy the fix", owner="Bob", due="Friday")]
    meeting.topics = [MeetingTopic(idx=0, topic="release")]
    session.add(meeting)
    await session.commit()
    return meeting


async def test_meeting_round_trips_with_children(db_session: AsyncSession):
    meeting = await _make_meeting(db_session)
    mid = meeting.id
    db_session.expunge_all()

    got = await db_session.get(Meeting, mid)
    assert got is not None
    assert got.status == MeetingStatus.uploaded  # python + server default applied
    assert got.duration_sec == 123.4

    segs = (
        await db_session.scalars(
            select(Segment).where(Segment.meeting_id == mid).order_by(Segment.idx)
        )
    ).all()
    assert [s.text for s in segs] == ["Hello everyone", "Hi, I pushed the fix"]

    summary = (await db_session.scalars(select(Summary).where(Summary.meeting_id == mid))).one()
    assert summary.attendees == ["Alice", "Bob"]
    assert summary.key_decisions == ["Ship Friday"]
    assert summary.open_questions == []  # jsonb default

    items = (await db_session.scalars(select(ActionItem).where(ActionItem.meeting_id == mid))).all()
    assert items[0].completed is False
    assert items[0].due == "Friday"


async def test_generated_tsvector_is_populated(db_session: AsyncSession):
    meeting = await _make_meeting(db_session)
    chunk = TranscriptChunk(
        meeting_id=meeting.id,
        idx=0,
        text="We migrated the Kubernetes deployment to the new cluster",
        start_sec=0.0,
        end_sec=5.0,
        embedding=[0.1] * 1536,
    )
    db_session.add(chunk)
    await db_session.commit()
    cid = chunk.id
    db_session.expunge_all()

    got = await db_session.get(TranscriptChunk, cid)
    assert got is not None
    assert got.ts is not None  # Computed STORED column filled by Postgres
    assert "kubernet" in got.ts  # english stemming


async def test_cascade_delete_removes_children(db_session: AsyncSession):
    meeting = await _make_meeting(db_session)
    mid = meeting.id
    await db_session.execute(text("DELETE FROM meetings WHERE id = :id"), {"id": str(mid)})
    await db_session.commit()

    segs = (await db_session.scalars(select(Segment).where(Segment.meeting_id == mid))).all()
    items = (await db_session.scalars(select(ActionItem).where(ActionItem.meeting_id == mid))).all()
    assert segs == []
    assert items == []


async def test_schema_has_extension_and_special_indexes(db_session: AsyncSession):
    ext = (
        await db_session.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
    ).scalar()
    assert ext == "vector"

    idx = (
        (
            await db_session.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename = 'transcript_chunks'")
            )
        )
        .scalars()
        .all()
    )
    assert "ix_chunks_embedding_hnsw" in idx
    assert "ix_chunks_ts" in idx
