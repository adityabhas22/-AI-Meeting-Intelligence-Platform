"""Archive analytics: speaking time per participant, meeting frequency, action-item
completion rate, and recurring topics. Plain relational aggregation, which is exactly
where keeping everything in one Postgres pays off."""

import uuid
from datetime import date

from pydantic import BaseModel
from sqlalchemy import String, and_, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActionItem, Meeting, MeetingTopic, Segment, Speaker

TOP_TOPICS = 10


class TalkTime(BaseModel):
    participant: str
    seconds: float


class TopicCount(BaseModel):
    topic: str
    count: int


class FrequencyBucket(BaseModel):
    period: date
    count: int


class CompletionStats(BaseModel):
    total: int
    completed: int
    rate: float


class AnalyticsSummary(BaseModel):
    total_meetings: int
    total_duration_sec: float
    action_items: CompletionStats
    meetings_per_week: list[FrequencyBucket]
    top_topics: list[TopicCount]
    talk_time: list[TalkTime]


def _participant_label():
    # Named speakers aggregate across meetings; unnamed fall back to "Speaker N".
    return func.coalesce(
        Speaker.display_name, func.concat("Speaker ", cast(Segment.speaker_label, String))
    )


async def speaking_time(
    session: AsyncSession, meeting_id: uuid.UUID | None = None
) -> list[TalkTime]:
    participant = _participant_label()
    duration = func.sum(Segment.end_sec - Segment.start_sec)
    stmt = (
        select(participant.label("participant"), duration.label("seconds"))
        .select_from(Segment)
        .join(
            Speaker,
            and_(Speaker.meeting_id == Segment.meeting_id, Speaker.label == Segment.speaker_label),
            isouter=True,
        )
        .group_by(participant)
        .order_by(duration.desc())
    )
    if meeting_id is not None:
        stmt = stmt.where(Segment.meeting_id == meeting_id)
    rows = (await session.execute(stmt)).all()
    return [TalkTime(participant=p, seconds=float(s or 0.0)) for p, s in rows]


async def get_analytics(session: AsyncSession) -> AnalyticsSummary:
    total_meetings = (await session.execute(select(func.count(Meeting.id)))).scalar_one()
    total_duration = (
        await session.execute(select(func.coalesce(func.sum(Meeting.duration_sec), 0.0)))
    ).scalar_one()

    total_items, completed_items = (
        await session.execute(
            select(
                func.count(ActionItem.id),
                func.count(ActionItem.id).filter(ActionItem.completed),
            )
        )
    ).one()
    rate = (completed_items / total_items) if total_items else 0.0

    week = func.date_trunc("week", Meeting.created_at)
    freq_rows = (
        await session.execute(
            select(week.label("period"), func.count(Meeting.id)).group_by(week).order_by(week)
        )
    ).all()

    topic_rows = (
        await session.execute(
            select(MeetingTopic.topic, func.count(MeetingTopic.id))
            .group_by(MeetingTopic.topic)
            .order_by(func.count(MeetingTopic.id).desc())
            .limit(TOP_TOPICS)
        )
    ).all()

    return AnalyticsSummary(
        total_meetings=total_meetings,
        total_duration_sec=float(total_duration),
        action_items=CompletionStats(total=total_items, completed=completed_items, rate=rate),
        meetings_per_week=[FrequencyBucket(period=p.date(), count=c) for p, c in freq_rows],
        top_topics=[TopicCount(topic=t, count=c) for t, c in topic_rows],
        talk_time=await speaking_time(session),
    )
