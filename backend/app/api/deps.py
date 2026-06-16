"""Injectable providers. The pipeline runner and the answerer are dependencies so
tests can override them with fakes (no Deepgram/OpenAI calls) while production wires
the real background pipeline and agent."""

import uuid
from collections.abc import Awaitable, Callable

from fastapi import BackgroundTasks

from app.agent.agent import AnswerResult, ask
from app.agent.agent import build_agent_session as _build_agent_session
from app.db import SessionLocal
from app.pipeline.pipeline import run_pipeline

PipelineRunner = Callable[[uuid.UUID, bytes], Awaitable[None]]
Answerer = Callable[..., Awaitable[AnswerResult]]


async def _run_pipeline_bg(meeting_id: uuid.UUID, audio: bytes) -> None:
    async with SessionLocal() as session:
        await run_pipeline(session, meeting_id, audio)


def get_pipeline_runner(background_tasks: BackgroundTasks) -> PipelineRunner:
    async def runner(meeting_id: uuid.UUID, audio: bytes) -> None:
        background_tasks.add_task(_run_pipeline_bg, meeting_id, audio)

    return runner


def get_answerer() -> Answerer:
    return ask


def build_agent_session(session_id: str):
    return _build_agent_session(session_id)
