"""The meeting-archive Q&A agent. Wraps the Agents SDK: one retrieval tool, optional
session memory, tracing on by default. Returns the answer plus the chunks the tool
surfaced so the API can show citations."""

from agents import Agent, Runner, set_default_openai_key
from agents.extensions.memory.sqlalchemy_session import SQLAlchemySession
from agents.memory.session import Session
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools import Deps, search_archive
from app.config import get_settings
from app.db import engine
from app.retrieval.retriever import Embedder, RetrievedChunk

_INSTRUCTIONS = (
    "You answer questions about the team's past meetings using only the meeting archive. "
    "Always call search_archive first to find relevant passages, and base your answer on "
    "what it returns. Cite the meetings you used by their title. If the archive has nothing "
    "relevant, say so plainly rather than guessing. Keep answers concise and specific."
)

_key_configured = False


def _configure_sdk() -> None:
    # The Agents SDK reads OPENAI_API_KEY from the process env; our key lives in .env,
    # so hand it to the SDK (and its tracing exporter) explicitly, once.
    global _key_configured
    if not _key_configured:
        set_default_openai_key(get_settings().openai_api_key)
        _key_configured = True


def build_agent(model: str | None = None) -> Agent:
    _configure_sdk()
    return Agent(
        name="Meeting Archive QA",
        instructions=_INSTRUCTIONS,
        model=model or get_settings().openai_model,
        tools=[search_archive],
    )


def build_agent_session(session_id: str) -> SQLAlchemySession:
    """Postgres-backed conversation memory, so follow-up questions keep context.
    Reuses the app engine; the SDK creates its own tables on first use."""
    return SQLAlchemySession(session_id, engine=engine, create_tables=True)


class AnswerResult(BaseModel):
    answer: str
    sources: list[RetrievedChunk]


async def ask(
    question: str,
    session: AsyncSession,
    *,
    embed: Embedder | None = None,
    model: str | None = None,
    agent_session: Session | None = None,
) -> AnswerResult:
    deps = Deps(session=session, embed=embed)
    result = await Runner.run(build_agent(model), question, context=deps, session=agent_session)
    return AnswerResult(answer=str(result.final_output), sources=deps.sources)
