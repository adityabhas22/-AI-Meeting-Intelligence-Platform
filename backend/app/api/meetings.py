import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
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

_AUDIO_EXTS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".aac",
    ".ogg",
    ".oga",
    ".opus",
    ".flac",
    ".webm",
    ".mp4",
    ".mov",
    ".mpeg",
    ".mpga",
}


def _looks_like_audio(filename: str, content_type: str | None) -> bool:
    if (content_type or "").lower().startswith(("audio/", "video/")):
        return True
    return Path(filename).suffix.lower() in _AUDIO_EXTS


def _parse_keyterms(raw: str | None) -> list[str]:
    if not raw:
        return []
    parts = (term.strip() for chunk in raw.splitlines() for term in chunk.split(","))
    return list(dict.fromkeys(t for t in parts if t))[:50]


@router.post("", response_model=schemas.UploadResponse, status_code=202)
async def upload_meeting(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    keyterms: str | None = Form(None),
    session: AsyncSession = Depends(get_session),
    runner: PipelineRunner = Depends(get_pipeline_runner),
) -> schemas.UploadResponse:
    name = file.filename or "audio"
    if not _looks_like_audio(name, file.content_type):
        raise HTTPException(
            status_code=415, detail="unsupported file type; upload an audio or video recording"
        )

    audio = await file.read()
    if not audio:
        raise HTTPException(status_code=400, detail="empty upload")
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    if len(audio) > max_bytes:
        raise HTTPException(
            status_code=413, detail=f"file exceeds {get_settings().max_upload_mb} MB limit"
        )

    meeting = Meeting(title=(title or "").strip() or name, filename=name)
    session.add(meeting)
    await session.commit()
    await runner(meeting.id, audio, _parse_keyterms(keyterms))
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
            .where(Meeting.deleted_at.is_(None))
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
            by_label[label].display_name = name.strip() or None
    await session.commit()

    meeting = await _load_meeting(session, meeting_id)
    talk = await speaking_time(session, meeting_id)
    return _to_detail(meeting, talk)


@router.patch("/{meeting_id}", response_model=schemas.MeetingDetail)
async def update_meeting(
    meeting_id: uuid.UUID,
    body: schemas.MeetingUpdate,
    session: AsyncSession = Depends(get_session),
) -> schemas.MeetingDetail:
    meeting = await _load_meeting(session, meeting_id)
    if body.title is not None and body.title.strip():
        meeting.title = body.title.strip()
    await session.commit()
    talk = await speaking_time(session, meeting_id)
    return _to_detail(meeting, talk)


@router.delete("/{meeting_id}", status_code=204)
async def delete_meeting(
    meeting_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> None:
    meeting = await session.get(Meeting, meeting_id)
    if meeting is None or meeting.deleted_at is not None:
        raise HTTPException(status_code=404, detail="meeting not found")
    meeting.deleted_at = datetime.now(UTC)  # soft delete: archived, recoverable
    await session.commit()


@router.post("/{meeting_id}/restore", response_model=schemas.MeetingDetail)
async def restore_meeting(
    meeting_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> schemas.MeetingDetail:
    meeting = await session.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="meeting not found")
    meeting.deleted_at = None
    await session.commit()
    meeting = await _load_meeting(session, meeting_id)
    talk = await speaking_time(session, meeting_id)
    return _to_detail(meeting, talk)


@router.post("/{meeting_id}/action-items", response_model=schemas.ActionItemOut, status_code=201)
async def add_action_item(
    meeting_id: uuid.UUID,
    body: schemas.ActionItemCreate,
    session: AsyncSession = Depends(get_session),
) -> schemas.ActionItemOut:
    meeting = await _load_meeting(session, meeting_id)
    next_idx = max((a.idx for a in meeting.action_items), default=-1) + 1
    item = ActionItem(
        meeting_id=meeting_id, idx=next_idx, task=body.task, owner=body.owner, due=body.due
    )
    session.add(item)
    await session.commit()
    return schemas.ActionItemOut(
        id=item.id, task=item.task, owner=item.owner, due=item.due, completed=item.completed
    )


async def _load_meeting(session: AsyncSession, meeting_id: uuid.UUID) -> Meeting:
    meeting = (
        await session.execute(
            select(Meeting)
            .where(Meeting.id == meeting_id, Meeting.deleted_at.is_(None))
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
