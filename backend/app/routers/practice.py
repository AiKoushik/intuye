"""Practice: rescue-phrase drill and shadowing both compare what you were asked to say with what was heard."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.curation.pronunciation import compare
from app.db import get_session
from app.models import User, UserSettings
from app.security.deps import current_user
from app.languages import default_variety

router = APIRouter(prefix="/v1/practice", tags=["practice"])


class CompareIn(BaseModel):
    expected: str = Field(min_length=1, max_length=300)
    heard: str = Field(default="", max_length=300)


@router.post("/compare")
async def compare_attempt(body: CompareIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    s = await db.get(UserSettings, user.id)
    return compare(body.expected, body.heard, s.dialect if s else default_variety())
