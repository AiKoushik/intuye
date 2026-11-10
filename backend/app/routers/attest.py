from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.security.deps import limit

router = APIRouter(prefix="/v1/attest", tags=["attest"], dependencies=[limit("attest", "auth_rate_limit_per_minute", by="ip")])


class RegisterIn(BaseModel):
    key_id: str = Field(min_length=10, max_length=100)
    attestation: str = Field(min_length=100, max_length=20000)
    challenge: str = Field(min_length=16, max_length=64)


@router.get("/challenge")
async def challenge(request: Request, db: AsyncSession = Depends(get_session)) -> dict:
    return {"challenge": await request.app.state.attest.new_challenge(db)}


@router.post("/register")
async def register(body: RegisterIn, request: Request, db: AsyncSession = Depends(get_session)) -> dict:
    await request.app.state.attest.register(db, body.key_id, body.attestation, body.challenge)
    return {"ok": True}
