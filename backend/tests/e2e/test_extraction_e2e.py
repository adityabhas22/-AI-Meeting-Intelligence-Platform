"""Opt-in e2e: real OpenAI call on the cheap dev model. Validates that our Pydantic
schema is accepted by structured outputs and that obvious tasks are captured.
Run with: uv run pytest -m e2e tests/e2e/test_extraction_e2e.py"""

import pytest

from app.extraction.extractor import extract_meeting

TRANSCRIPT = """\
Speaker 0: Welcome to the release planning meeting. We need to decide the ship date.
Speaker 1: I think we ship Friday. Bob, can you deploy the auth fix by then?
Speaker 2: Yes, I will deploy the auth fix by Friday.
Speaker 0: Good. One open question: do we need a feature flag for the rollout?
Speaker 1: Let's also schedule a follow-up next week to review metrics."""


@pytest.mark.e2e
def test_real_extraction_returns_structured_output():
    result = extract_meeting(TRANSCRIPT)

    assert result.title.strip()
    assert result.overview.strip()
    assert len(result.action_items) >= 1
    assert any("auth" in item.task.lower() for item in result.action_items)
    assert any("flag" in q.lower() for q in result.open_questions)
