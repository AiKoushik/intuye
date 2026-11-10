from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import User, UserSettings
from app.security.deps import limit

router = APIRouter(prefix="/v1/auth", tags=["auth"], dependencies=[limit("auth", "auth_rate_limit_per_minute", by="ip")])


class AppleSignIn(BaseModel):
    identity_token: str = Field(min_length=20, max_length=4096)
    raw_nonce: str = Field(min_length=16, max_length=128)
    display_name: str | None = Field(default=None, max_length=120)


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=200)


class UserOut(BaseModel):
    id: str
    display_name: str | None


class SessionOut(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"
    user: UserOut | None = None


@router.post("/apple", response_model=SessionOut)
async def sign_in_with_apple(body: AppleSignIn, request: Request, db: AsyncSession = Depends(get_session)) -> SessionOut:
    claims = await request.app.state.apple.verify(body.identity_token, body.raw_nonce)
    user = (await db.execute(select(User).where(User.apple_sub == claims["sub"]))).scalar_one_or_none()
    if user is None:
        user = User(apple_sub=claims["sub"], display_name=body.display_name)
        db.add(user)
        await db.flush()
        db.add(UserSettings(user_id=user.id))
    elif body.display_name and not user.display_name:
        user.display_name = body.display_name
    await db.commit()
    await request.app.state.attest.bind_user(db, request, user.id)
    pair = await request.app.state.tokens.start_session(db, user.id)
    return SessionOut(**pair.__dict__, user=UserOut(id=user.id, display_name=user.display_name))


@router.post("/refresh", response_model=SessionOut)
async def refresh(body: RefreshIn, request: Request, db: AsyncSession = Depends(get_session)) -> SessionOut:
    pair = await request.app.state.tokens.rotate(db, body.refresh_token)
    return SessionOut(**pair.__dict__)


@router.post("/logout", status_code=204)
async def logout(body: RefreshIn, request: Request, db: AsyncSession = Depends(get_session)) -> Response:
    await request.app.state.tokens.revoke(db, body.refresh_token)
    return Response(status_code=204)
