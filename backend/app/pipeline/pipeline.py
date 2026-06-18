"""The ingestion pipeline: transcribe, persist the transcript, extract structure,
then index for search. Status is committed between stages so a polling client sees
progress. Blocking SDK calls run in a thread so the event loop stays responsive.

run_pipeline takes the session (it does not own it) so it can run inside a test's
rollback transaction as well as a real background-task session.
"""

import asyncio
import logging
import uuid
from collections.abc import Callable

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.extraction.extractor import extract_meeting
from app.extraction.schema import MeetingExtraction
from app.indexing.chunker import chunk_segments
from app.indexing.embeddings import embed_texts
from app.indexing.indexer import persist_chunks
from app.models import ActionItem, Meeting, MeetingStatus, MeetingTopic, Segment, Speaker, Summary
from app.transcription.deepgram import transcribe
from app.transcription.models import TranscriptionResult

TranscribeFn = Callable[..., TranscriptionResult]
ExtractFn = Callable[..., MeetingExtraction]
EmbedFn = Callable[[list[str]], list[list[float]]]

logger = logging.getLogger(__name__)

_PROCESSING_STATUSES = [
    MeetingStatus.uploaded,
    MeetingStatus.transcribing,
    MeetingStatus.extracting,
    MeetingStatus.indexing,
]


async def fail_stranded_meetings(session: AsyncSession) -> int:
    """Mark meetings stuck in a processing state (from a previous crash/restart) as
    failed, so they don't poll forever. Returns the number recovered."""
    result = await session.execute(
        update(Meeting)
        .where(Meeting.status.in_(_PROCESSING_STATUSES))
        .values(
            status=MeetingStatus.failed,
            error="Processing was interrupted by a server restart.",
        )
    )
    await session.commit()
    return result.rowcount or 0


async def run_pipeline(
    session: AsyncSession,
    meeting_id: uuid.UUID,
    audio: bytes,
    *,
    keyterms: list[str] | None = None,
    transcribe_fn: TranscribeFn = transcribe,
    extract_fn: ExtractFn = extract_meeting,
    embed_fn: EmbedFn = embed_texts,
) -> None:
    meeting = await session.get(Meeting, meeting_id)
    if meeting is None:
        raise ValueError(f"meeting {meeting_id} not found")

    logger.info("pipeline start: meeting=%s bytes=%d", meeting_id, len(audio))
    try:
        meeting.status = MeetingStatus.transcribing
        await session.commit()

        result = await asyncio.to_thread(transcribe_fn, audio, keyterms=keyterms)
        if not result.segments:
            meeting.status = MeetingStatus.failed
            meeting.error = "No speech detected in the recording."
            await session.commit()
            logger.warning("pipeline aborted: meeting=%s had no speech", meeting_id)
            return
        _save_transcript(session, meeting, result)
        logger.info(
            "transcribed: meeting=%s segments=%d speakers=%d",
            meeting_id,
            len(result.segments),
            result.num_speakers,
        )

        meeting.status = MeetingStatus.extracting
        await session.commit()

        extraction = await asyncio.to_thread(extract_fn, result.labelled_text())
        _save_extraction(session, meeting, extraction)

        meeting.status = MeetingStatus.indexing
        await session.commit()

        chunks = chunk_segments(result.segments)
        if chunks:
            vectors = await asyncio.to_thread(embed_fn, [c.text for c in chunks])
            await persist_chunks(session, meeting_id, chunks, vectors)

        meeting.status = MeetingStatus.done
        await session.commit()
        logger.info("pipeline done: meeting=%s", meeting_id)
    except Exception as exc:
        logger.exception("pipeline failed: meeting=%s", meeting_id)
        await session.rollback()
        meeting = await session.get(Meeting, meeting_id)
        if meeting is not None:
            meeting.status = MeetingStatus.failed
            meeting.error = str(exc)[:1000]
            await session.commit()
        raise


def _save_transcript(session: AsyncSession, meeting: Meeting, result: TranscriptionResult) -> None:
    meeting.duration_sec = result.duration_sec
    meeting.language = result.language
    labels = sorted({s.speaker_label for s in result.segments})
    session.add_all([Speaker(meeting_id=meeting.id, label=label) for label in labels])
    session.add_all(
        [
            Segment(
                meeting_id=meeting.id,
                idx=s.idx,
                speaker_label=s.speaker_label,
                start_sec=s.start_sec,
                end_sec=s.end_sec,
                text=s.text,
            )
            for s in result.segments
        ]
    )


def _save_extraction(
    session: AsyncSession, meeting: Meeting, extraction: MeetingExtraction
) -> None:
    # Only adopt the model's title when the user did not set one (title still the filename).
    if extraction.title and meeting.title == meeting.filename:
        meeting.title = extraction.title
    session.add(
        Summary(
            meeting_id=meeting.id,
            overview=extraction.overview,
            attendees=extraction.attendees,
            key_decisions=extraction.key_decisions,
            discussion_points=extraction.discussion_points,
            open_questions=extraction.open_questions,
            next_steps=extraction.next_steps,
        )
    )
    session.add_all(
        [
            ActionItem(meeting_id=meeting.id, idx=i, task=item.task, owner=item.owner, due=item.due)
            for i, item in enumerate(extraction.action_items)
        ]
    )
    session.add_all(
        [
            MeetingTopic(meeting_id=meeting.id, idx=i, topic=topic)
            for i, topic in enumerate(extraction.topics)
        ]
    )
