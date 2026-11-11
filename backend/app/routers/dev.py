"""Development-only sign-in for the web test client (Sign in with Apple needs a real app or domain).

Registered only when DEV_LOGIN_ENABLED=true and ENV != production (Settings refuses the combination).
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import User, UserSettings
from app.routers.auth import SessionOut, UserOut
from app.security.deps import limit

router = APIRouter(prefix="/v1/auth", tags=["dev"], dependencies=[limit("auth", "auth_rate_limit_per_minute", by="ip")])


class DevSignIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)


@router.post("/dev", response_model=SessionOut)
async def dev_sign_in(body: DevSignIn, request: Request, db: AsyncSession = Depends(get_session)) -> SessionOut:
    slug = re.sub(r"[^a-z0-9]+", "-", body.name.strip().lower()).strip("-") or "tester"
    sub = f"dev:{slug}"
    user = (await db.execute(select(User).where(User.apple_sub == sub))).scalar_one_or_none()
    if user is None:
        user = User(apple_sub=sub, display_name=body.name.strip())
        db.add(user)
        await db.flush()
        db.add(UserSettings(user_id=user.id))
        await db.commit()
    pair = await request.app.state.tokens.start_session(db, user.id)
    return SessionOut(**pair.__dict__, user=UserOut(id=user.id, display_name=user.display_name))
