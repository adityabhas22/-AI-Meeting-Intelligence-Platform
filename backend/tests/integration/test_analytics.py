from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.service import get_analytics, speaking_time
from app.models import ActionItem, Meeting, MeetingTopic, Segment, Speaker


async def _seed(session: AsyncSession) -> Meeting:
    m1 = Meeting(title="Planning", filename="a.m4a", duration_sec=100.0)
    m1.speakers = [Speaker(label=0, display_name="Alice"), Speaker(label=1, display_name="Bob")]
    m1.segments = [
        Segment(idx=0, speaker_label=0, start_sec=0.0, end_sec=15.0, text="a"),  # Alice 15
        Segment(idx=1, speaker_label=1, start_sec=15.0, end_sec=30.0, text="b"),  # Bob 15
        Segment(idx=2, speaker_label=0, start_sec=30.0, end_sec=40.0, text="c"),  # Alice 10
    ]
    m1.action_items = [
        ActionItem(idx=0, task="x", completed=True),
        ActionItem(idx=1, task="y", completed=False),
    ]
    m1.topics = [MeetingTopic(idx=0, topic="release"), MeetingTopic(idx=1, topic="auth")]

    m2 = Meeting(title="Sync", filename="b.m4a", duration_sec=200.0)
    m2.speakers = [Speaker(label=0, display_name="Alice")]
    m2.segments = [
        Segment(idx=0, speaker_label=0, start_sec=0.0, end_sec=20.0, text="d")
    ]  # Alice 20
    m2.action_items = [ActionItem(idx=0, task="z", completed=False)]
    m2.topics = [MeetingTopic(idx=0, topic="release")]

    session.add_all([m1, m2])
    await session.commit()
    return m1


async def test_archive_analytics_aggregate_correctly(db_session: AsyncSession):
    m1 = await _seed(db_session)
    summary = await get_analytics(db_session)

    assert summary.total_meetings == 2
    assert summary.total_duration_sec == 300.0
    assert summary.action_items.total == 3
    assert summary.action_items.completed == 1
    assert round(summary.action_items.rate, 2) == 0.33

    topics = {t.topic: t.count for t in summary.top_topics}
    assert topics == {"release": 2, "auth": 1}

    talk = {t.participant: t.seconds for t in summary.talk_time}
    assert talk == {"Alice": 45.0, "Bob": 15.0}
    assert summary.talk_time[0].participant == "Alice"  # ordered by time desc

    assert len(summary.meetings_per_week) == 1  # both created this week
    assert summary.meetings_per_week[0].count == 2

    per_meeting = {t.participant: t.seconds for t in await speaking_time(db_session, m1.id)}
    assert per_meeting == {"Alice": 25.0, "Bob": 15.0}


async def test_empty_archive_analytics(db_session: AsyncSession):
    summary = await get_analytics(db_session)
    assert summary.total_meetings == 0
    assert summary.total_duration_sec == 0.0
    assert summary.action_items.rate == 0.0
    assert summary.top_topics == []
    assert summary.talk_time == []
