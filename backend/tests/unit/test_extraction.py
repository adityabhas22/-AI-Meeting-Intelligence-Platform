import pytest

from app.extraction.extractor import extract_meeting
from app.extraction.schema import ExtractedActionItem, MeetingExtraction

SAMPLE = MeetingExtraction(
    title="Sprint planning",
    overview="The team planned the sprint and assigned the auth work.",
    attendees=["Alice", "Bob"],
    key_decisions=["Ship the auth fix Friday"],
    discussion_points=["Auth bug", "Release timing"],
    open_questions=["Do we need a feature flag?"],
    next_steps=["Schedule a follow-up"],
    action_items=[ExtractedActionItem(task="Deploy the auth fix", owner="Bob", due="Friday")],
    topics=["auth", "release"],
)


class _FakeResponses:
    def __init__(self, parsed: MeetingExtraction):
        self._parsed = parsed
        self.captured: dict = {}

    def parse(self, **kwargs):
        self.captured = kwargs
        return type("Resp", (), {"output_parsed": self._parsed})()


class _FakeClient:
    def __init__(self, parsed: MeetingExtraction | None):
        self.responses = _FakeResponses(parsed)


def test_extract_passes_schema_and_transcript_and_returns_parsed():
    fake = _FakeClient(SAMPLE)
    result = extract_meeting("Speaker 0: Let's plan the sprint.", client=fake, model="gpt-5-mini")

    assert result is SAMPLE
    sent = fake.responses.captured
    assert sent["model"] == "gpt-5-mini"
    assert sent["text_format"] is MeetingExtraction
    assert "Speaker 0: Let's plan the sprint." in str(sent["input"])


def test_extract_raises_when_model_returns_nothing():
    fake = _FakeClient(None)
    with pytest.raises(ValueError, match="no structured extraction"):
        extract_meeting("Speaker 0: hi", client=fake, model="gpt-5-mini")
