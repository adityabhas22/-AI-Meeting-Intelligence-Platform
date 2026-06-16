from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import schemas
from app.api.deps import Answerer, build_agent_session, get_answerer
from app.db import get_session

router = APIRouter(tags=["ask"])


@router.post("/ask", response_model=schemas.AskResponse)
async def ask_question(
    body: schemas.AskRequest,
    session: AsyncSession = Depends(get_session),
    answerer: Answerer = Depends(get_answerer),
) -> schemas.AskResponse:
    agent_session = build_agent_session(body.session_id) if body.session_id else None
    result = await answerer(body.question, session, agent_session=agent_session)
    return schemas.AskResponse(answer=result.answer, sources=result.sources)
