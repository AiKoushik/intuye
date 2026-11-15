from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import APIError
from app.models import SceneTemplate, User, UserSettings
from app.security.deps import current_user
from app.services import library
from app.services.scenarios import serialise
from app.languages import default_variety

router = APIRouter(prefix="/v1/library", tags=["library"])


class UseIn(BaseModel):
    starts_at: datetime | None = None
    kind: Literal["manual", "upcoming"] = "manual"


class ReportIn(BaseModel):
    reason: Literal["personal", "offensive", "wrong", "other"]


async def _dialect(db: AsyncSession, user_id: str) -> str:
    s = await db.get(UserSettings, user_id)
    return s.dialect if s else default_variety()


async def _published(db: AsyncSession, template_id: str) -> SceneTemplate:
    t = await db.get(SceneTemplate, template_id)
    if t is None or t.status != "published":
        raise APIError(404, "not_found", "That scene isn't in the library.")
    return t


@router.get("")
async def search(request: Request, q: str = Query("", max_length=200), limit: int = Query(10, ge=1, le=20),
                 user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    return {"results": await library.search(db, request.app.state.library, await _dialect(db, user.id), q, limit)}


@router.get("/{template_id}")
async def detail(template_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    t = await _published(db, template_id)
    return library.card(t) | {"level": t.level, "phrases": library.phrases(t)}


@router.post("/{template_id}/use")
async def use(template_id: str, body: UseIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    t = await _published(db, template_id)
    starts = body.starts_at if body.starts_at is None or body.starts_at.tzinfo else body.starts_at.replace(tzinfo=timezone.utc)
    s = await library.use(db, user, t, starts, body.kind)
    return await serialise(db, s, with_phrases=True)


@router.post("/{template_id}/report")
async def report(template_id: str, body: ReportIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    await library.report(db, user, await _published(db, template_id), body.reason)
    return {"ok": True}
