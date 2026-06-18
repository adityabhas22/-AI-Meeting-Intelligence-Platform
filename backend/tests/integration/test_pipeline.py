import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActionItem, Meeting, MeetingStatus, Segment, Summary, TranscriptChunk
from app.pipeline.pipeline import fail_stranded_meetings, run_pipeline
from app.transcription.models import TranscriptionResult


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


async def test_pipeline_aborts_when_no_speech(db_session: AsyncSession):
    meeting = Meeting(title="silent.m4a", filename="silent.m4a")
    db_session.add(meeting)
    await db_session.commit()
    mid = meeting.id

    def silent(audio, *, keyterms=None):
        return TranscriptionResult(segments=[], duration_sec=0.0, language=None)

    await run_pipeline(db_session, mid, b"audio", transcribe_fn=silent)
    db_session.expunge_all()

    got = await db_session.get(Meeting, mid)
    assert got.status == MeetingStatus.failed
    assert "no speech" in (got.error or "").lower()
    # extraction and indexing were skipped
    assert (
        await db_session.scalars(select(Summary).where(Summary.meeting_id == mid))
    ).first() is None
    assert (
        await db_session.scalars(select(TranscriptChunk).where(TranscriptChunk.meeting_id == mid))
    ).first() is None


async def test_fail_stranded_meetings_recovers_processing_rows(db_session: AsyncSession):
    stuck = Meeting(title="a", filename="a", status=MeetingStatus.transcribing)
    indexing = Meeting(title="b", filename="b", status=MeetingStatus.indexing)
    finished = Meeting(title="c", filename="c", status=MeetingStatus.done)
    db_session.add_all([stuck, indexing, finished])
    await db_session.commit()

    recovered = await fail_stranded_meetings(db_session)
    db_session.expunge_all()

    assert recovered == 2
    assert (await db_session.get(Meeting, stuck.id)).status == MeetingStatus.failed
    assert (await db_session.get(Meeting, indexing.id)).status == MeetingStatus.failed
    assert (await db_session.get(Meeting, finished.id)).status == MeetingStatus.done
