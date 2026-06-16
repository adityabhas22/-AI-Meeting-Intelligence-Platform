"""The shape we ask the model to fill. Field descriptions are sent to the model as
part of the JSON schema, so they double as extraction instructions."""

from pydantic import BaseModel, Field


class ExtractedActionItem(BaseModel):
    task: str = Field(description="The concrete commitment or task, phrased as an imperative.")
    owner: str | None = Field(
        default=None, description="Person responsible, if one is named. Null otherwise."
    )
    due: str | None = Field(
        default=None,
        description="Deadline exactly as stated, e.g. 'next Friday' or 'end of Q3'. Null if none.",
    )


class MeetingExtraction(BaseModel):
    title: str = Field(description="Short descriptive meeting title, at most about eight words.")
    overview: str = Field(description="A two or three sentence summary of the meeting.")
    attendees: list[str] = Field(description="Names or roles of the people who took part.")
    key_decisions: list[str] = Field(description="Concrete decisions the group reached.")
    discussion_points: list[str] = Field(description="The main things discussed.")
    open_questions: list[str] = Field(description="Questions raised but left unresolved.")
    next_steps: list[str] = Field(
        description="Planned follow-ups that are not a single person's action item."
    )
    action_items: list[ExtractedActionItem] = Field(
        description="Every explicitly stated task. Do not invent any that were not said."
    )
    topics: list[str] = Field(
        description="Short topic tags for archive search, e.g. 'pricing', 'hiring', 'auth'."
    )
