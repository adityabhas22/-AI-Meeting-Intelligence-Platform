"""The ingestion pipeline: transcribe, persist the transcript, extract structure,
then index for search. Status is committed between stages so a polling client sees
progress. Blocking SDK calls run in a thread so the event loop stays responsive.

run_pipeline takes the session (it does not own it) so it can run inside a test's
rollback transaction as well as a real background-task session.
"""

import asyncio
import uuid
from collections.abc import Callable

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

    try:
        meeting.status = MeetingStatus.transcribing
        await session.commit()

        result = await asyncio.to_thread(transcribe_fn, audio, keyterms=keyterms)
        _save_transcript(session, meeting, result)

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
    except Exception as exc:
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
    if extraction.title:
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
