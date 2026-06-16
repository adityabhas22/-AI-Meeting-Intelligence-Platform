from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.service import AnalyticsSummary, get_analytics
from app.db import get_session

router = APIRouter(tags=["analytics"])


@router.get("/analytics", response_model=AnalyticsSummary)
async def analytics(session: AsyncSession = Depends(get_session)) -> AnalyticsSummary:
    return await get_analytics(session)
