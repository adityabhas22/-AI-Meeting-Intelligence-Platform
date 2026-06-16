import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.agent import ask
from app.agent.tools import Deps, archive_search
from app.models import Meeting, TranscriptChunk


def _vec(i: int) -> list[float]:
    v = [0.0] * 1536
    v[i] = 1.0
    return v


async def _seed(session: AsyncSession) -> Meeting:
    meeting = Meeting(title="Ops sync", filename="ops.m4a")
    session.add(meeting)
    await session.flush()
    session.add(
        TranscriptChunk(
            meeting_id=meeting.id,
            idx=0,
            text="We deployed the kubernetes cluster upgrade this morning",
            start_sec=0.0,
            end_sec=5.0,
            embedding=_vec(0),
        )
    )
    await session.commit()
    return meeting


async def test_archive_search_formats_and_records_sources(db_session: AsyncSession):
    await _seed(db_session)
    deps = Deps(session=db_session, embed=lambda _t: [_vec(0)])
    out = await archive_search(deps, "kubernetes")
    assert "Ops sync" in out
    assert "kubernetes" in out.lower()
    assert len(deps.sources) == 1
    assert deps.sources[0].meeting_title == "Ops sync"


@pytest.mark.e2e
async def test_agent_answers_from_archive_with_real_llm(db_session: AsyncSession):
    await _seed(db_session)
    result = await ask("What did we deploy this morning?", db_session, embed=lambda _t: [_vec(0)])
    assert result.answer.strip()
    assert result.sources  # the agent actually used the tool
    assert "kubernetes" in result.answer.lower()
