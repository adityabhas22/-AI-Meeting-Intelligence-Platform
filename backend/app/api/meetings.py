import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analytics.service import TalkTime, speaking_time
from app.api import schemas
from app.api.deps import PipelineRunner, get_pipeline_runner
from app.config import get_settings
from app.db import get_session
from app.models import ActionItem, Meeting, Speaker

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.post("", response_model=schemas.UploadResponse, status_code=202)
async def upload_meeting(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    runner: PipelineRunner = Depends(get_pipeline_runner),
) -> schemas.UploadResponse:
    audio = await file.read()
    if not audio:
        raise HTTPException(status_code=400, detail="empty upload")
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    if len(audio) > max_bytes:
        raise HTTPException(
            status_code=413, detail=f"file exceeds {get_settings().max_upload_mb} MB limit"
        )

    name = file.filename or "audio"
    meeting = Meeting(title=name, filename=name)
    session.add(meeting)
    await session.commit()
    await runner(meeting.id, audio)
    return schemas.UploadResponse(id=meeting.id, status=meeting.status)


@router.get("", response_model=list[schemas.MeetingListItem])
async def list_meetings(
    session: AsyncSession = Depends(get_session),
) -> list[schemas.MeetingListItem]:
    counts = (
        select(ActionItem.meeting_id, func.count(ActionItem.id).label("c"))
        .group_by(ActionItem.meeting_id)
        .subquery()
    )
    rows = (
        await session.execute(
            select(Meeting, func.coalesce(counts.c.c, 0))
            .outerjoin(counts, counts.c.meeting_id == Meeting.id)
            .order_by(Meeting.created_at.desc())
        )
    ).all()
    return [
        schemas.MeetingListItem(
            id=m.id,
            title=m.title,
            filename=m.filename,
            status=m.status,
            duration_sec=m.duration_sec,
            created_at=m.created_at,
            action_item_count=count,
        )
        for m, count in rows
    ]


@router.get("/{meeting_id}", response_model=schemas.MeetingDetail)
async def get_meeting(
    meeting_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> schemas.MeetingDetail:
    meeting = await _load_meeting(session, meeting_id)
    talk = await speaking_time(session, meeting_id)
    return _to_detail(meeting, talk)


@router.patch("/{meeting_id}/speakers", response_model=schemas.MeetingDetail)
async def rename_speakers(
    meeting_id: uuid.UUID,
    body: schemas.SpeakerRenameRequest,
    session: AsyncSession = Depends(get_session),
) -> schemas.MeetingDetail:
    speakers = (
        await session.scalars(select(Speaker).where(Speaker.meeting_id == meeting_id))
    ).all()
    if not speakers:
        raise HTTPException(status_code=404, detail="meeting not found or has no speakers")
    by_label = {s.label: s for s in speakers}
    for label, name in body.names.items():
        if label in by_label:
            by_label[label].display_name = name
    await session.commit()

    meeting = await _load_meeting(session, meeting_id)
    talk = await speaking_time(session, meeting_id)
    return _to_detail(meeting, talk)


async def _load_meeting(session: AsyncSession, meeting_id: uuid.UUID) -> Meeting:
    meeting = (
        await session.execute(
            select(Meeting)
            .where(Meeting.id == meeting_id)
            .options(
                selectinload(Meeting.speakers),
                selectinload(Meeting.segments),
                selectinload(Meeting.summary),
                selectinload(Meeting.action_items),
                selectinload(Meeting.topics),
            )
        )
    ).scalar_one_or_none()
    if meeting is None:
        raise HTTPException(status_code=404, detail="meeting not found")
    return meeting


def _to_detail(meeting: Meeting, talk: list[TalkTime]) -> schemas.MeetingDetail:
    summary = None
    if meeting.summary is not None:
        s = meeting.summary
        summary = schemas.SummaryOut(
            overview=s.overview,
            attendees=s.attendees,
            key_decisions=s.key_decisions,
            discussion_points=s.discussion_points,
            open_questions=s.open_questions,
            next_steps=s.next_steps,
        )
    return schemas.MeetingDetail(
        id=meeting.id,
        title=meeting.title,
        filename=meeting.filename,
        status=meeting.status,
        error=meeting.error,
        duration_sec=meeting.duration_sec,
        language=meeting.language,
        created_at=meeting.created_at,
        speakers=[
            schemas.SpeakerOut(label=sp.label, display_name=sp.display_name)
            for sp in sorted(meeting.speakers, key=lambda x: x.label)
        ],
        segments=[
            schemas.SegmentOut(
                idx=seg.idx,
                speaker_label=seg.speaker_label,
                start_sec=seg.start_sec,
                end_sec=seg.end_sec,
                text=seg.text,
            )
            for seg in meeting.segments
        ],
        summary=summary,
        action_items=[
            schemas.ActionItemOut(
                id=ai.id, task=ai.task, owner=ai.owner, due=ai.due, completed=ai.completed
            )
            for ai in meeting.action_items
        ],
        topics=[t.topic for t in sorted(meeting.topics, key=lambda x: x.idx)],
        talk_time=talk,
    )
