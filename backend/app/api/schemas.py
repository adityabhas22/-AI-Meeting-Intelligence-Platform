"""Request and response shapes for the API. Kept separate from the ORM so the wire
contract is explicit and stable."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.analytics.service import TalkTime
from app.models import MeetingStatus
from app.retrieval.retriever import RetrievedChunk


class SpeakerOut(BaseModel):
    label: int
    display_name: str | None


class SegmentOut(BaseModel):
    idx: int
    speaker_label: int
    start_sec: float
    end_sec: float
    text: str


class SummaryOut(BaseModel):
    overview: str
    attendees: list[str]
    key_decisions: list[str]
    discussion_points: list[str]
    open_questions: list[str]
    next_steps: list[str]


class ActionItemOut(BaseModel):
    id: uuid.UUID
    task: str
    owner: str | None
    due: str | None
    completed: bool


class MeetingListItem(BaseModel):
    id: uuid.UUID
    title: str
    filename: str
    status: MeetingStatus
    duration_sec: float | None
    created_at: datetime
    action_item_count: int


class MeetingDetail(BaseModel):
    id: uuid.UUID
    title: str
    filename: str
    status: MeetingStatus
    error: str | None
    duration_sec: float | None
    language: str | None
    created_at: datetime
    speakers: list[SpeakerOut]
    segments: list[SegmentOut]
    summary: SummaryOut | None
    action_items: list[ActionItemOut]
    topics: list[str]
    talk_time: list[TalkTime]


class UploadResponse(BaseModel):
    id: uuid.UUID
    status: MeetingStatus


class SpeakerRenameRequest(BaseModel):
    names: dict[int, str]  # speaker label -> display name


class ActionItemUpdate(BaseModel):
    completed: bool | None = None
    task: str | None = None
    owner: str | None = None
    due: str | None = None


class AskRequest(BaseModel):
    question: str
    session_id: str | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list[RetrievedChunk]
