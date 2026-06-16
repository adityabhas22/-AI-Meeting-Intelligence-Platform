"""Structured extraction over a speaker-labelled transcript via the OpenAI Responses
API. The client is injectable so tests run without the network or any cost."""

from openai import OpenAI

from app.config import get_settings
from app.extraction.schema import MeetingExtraction

_INSTRUCTIONS = (
    "You extract structured intelligence from a meeting transcript labelled by speaker. "
    "Produce a concise title and a short overview, then the attendees, key decisions, "
    "discussion points, open questions, and next steps. Extract every action item that is "
    "explicitly stated, with its owner and deadline when mentioned, and do not invent tasks "
    "that were not said. Add a few short topic tags useful for searching an archive later. "
    "If a section has nothing, return an empty list rather than guessing."
)


def extract_meeting(
    transcript: str,
    *,
    client: OpenAI | None = None,
    model: str | None = None,
) -> MeetingExtraction:
    settings = get_settings()
    client = client or OpenAI(api_key=settings.openai_api_key)
    response = client.responses.parse(
        model=model or settings.openai_model,
        reasoning={"effort": "low"},  # extraction is structured, not a reasoning marathon
        input=[
            {"role": "system", "content": _INSTRUCTIONS},
            {"role": "user", "content": transcript},
        ],
        text_format=MeetingExtraction,
    )
    parsed = response.output_parsed
    if parsed is None:
        raise ValueError("model returned no structured extraction")
    return parsed
