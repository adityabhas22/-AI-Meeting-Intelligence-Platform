import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import schemas
from app.db import get_session
from app.models import ActionItem

router = APIRouter(prefix="/action-items", tags=["action-items"])


@router.patch("/{item_id}", response_model=schemas.ActionItemOut)
async def update_action_item(
    item_id: uuid.UUID,
    body: schemas.ActionItemUpdate,
    session: AsyncSession = Depends(get_session),
) -> schemas.ActionItemOut:
    item = await session.get(ActionItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="action item not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await session.commit()
    return schemas.ActionItemOut(
        id=item.id, task=item.task, owner=item.owner, due=item.due, completed=item.completed
    )


@router.delete("/{item_id}", status_code=204)
async def delete_action_item(
    item_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> None:
    item = await session.get(ActionItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="action item not found")
    await session.delete(item)
    await session.commit()
