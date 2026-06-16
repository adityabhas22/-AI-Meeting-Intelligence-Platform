import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActionItem, Meeting, MeetingStatus, Segment, Summary, TranscriptChunk
from app.pipeline.pipeline import run_pipeline


async def test_pipeline_processes_meeting_end_to_end(db_session: AsyncSession, pipeline_fakes):
    meeting = Meeting(title="raw.m4a", filename="raw.m4a")
    db_session.add(meeting)
    await db_session.commit()
    mid = meeting.id

    await run_pipeline(db_session, mid, b"audio-bytes", **pipeline_fakes)
    db_session.expunge_all()

    got = await db_session.get(Meeting, mid)
    assert got.status == MeetingStatus.done
    assert got.duration_sec == 10.0
    assert got.language == "en"
    assert got.title == "Release planning"  # title taken from extraction

    segments = (await db_session.scalars(select(Segment).where(Segment.meeting_id == mid))).all()
    assert len(segments) == 2

    summary = (await db_session.scalars(select(Summary).where(Summary.meeting_id == mid))).one()
    assert summary.key_decisions == ["Ship Friday"]

    items = (await db_session.scalars(select(ActionItem).where(ActionItem.meeting_id == mid))).all()
    assert [i.task for i in items] == ["Deploy the auth fix"]

    chunks = (
        await db_session.scalars(select(TranscriptChunk).where(TranscriptChunk.meeting_id == mid))
    ).all()
    assert len(chunks) >= 1
    assert all(c.ts is not None for c in chunks)


async def test_pipeline_marks_failed_on_error(db_session: AsyncSession):
    meeting = Meeting(title="raw.m4a", filename="raw.m4a")
    db_session.add(meeting)
    await db_session.commit()
    mid = meeting.id

    def boom(audio, *, keyterms=None):
        raise RuntimeError("transcription service down")

    with pytest.raises(RuntimeError):
        await run_pipeline(db_session, mid, b"audio", transcribe_fn=boom)

    db_session.expunge_all()
    got = await db_session.get(Meeting, mid)
    assert got.status == MeetingStatus.failed
    assert "transcription service down" in got.error
