"""FastAPI dependencies: who is calling (bearer) and per-route rate limits."""
from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import APIError
from app.models import User


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


async def current_user(request: Request, db: AsyncSession = Depends(get_session)) -> User:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise APIError(401, "missing_token", "Sign in to continue.")
    claims = request.app.state.tokens.decode_access(header[7:].strip())
    user = await db.get(User, claims["sub"])
    if user is None:
        raise APIError(401, "invalid_token", "Account not found.")
    s = request.app.state.settings
    request.app.state.ratelimiter.check(f"user:{user.id}", s.rate_limit_per_minute)
    request.state.user_id = user.id
    return user


def limit(bucket: str, per_minute_attr: str, by: str = "user"):
    """Extra rate limit for expensive or sensitive routes."""

    async def dep(request: Request) -> None:
        s = request.app.state.settings
        key = getattr(request.state, "user_id", None) if by == "user" else None
        request.app.state.ratelimiter.check(f"{bucket}:{key or client_ip(request)}", getattr(s, per_minute_attr))

    return Depends(dep)
