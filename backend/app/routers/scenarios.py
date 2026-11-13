from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import APIError
from app.models import Readiness, Scenario, ScenarioPhrase, User, utcnow
from app.security.deps import current_user, limit
from app.services.scenarios import prepare, serialise

router = APIRouter(prefix="/v1/scenarios", tags=["scenarios"])
CALENDAR_HORIZON = timedelta(days=14)


def _aware(dt: datetime | None) -> datetime | None:
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class ScenarioIn(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    starts_at: datetime | None = None
    kind: Literal["manual", "upcoming"] = "manual"


class CalendarEvent(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    starts_at: datetime


class CalendarIn(BaseModel):
    events: list[CalendarEvent] = Field(max_length=20)


class ReadinessIn(BaseModel):
    value: int = Field(ge=1, le=5)
    phase: Literal["before", "after"]


class StatusIn(BaseModel):
    status: Literal["active", "done"]


async def _owned(db: AsyncSession, user_id: str, scenario_id: str) -> Scenario:
    s = (await db.execute(select(Scenario).where(Scenario.id == scenario_id, Scenario.user_id == user_id))).scalar_one_or_none()
    if s is None:
        raise APIError(404, "not_found", "That scene doesn't exist.")
    return s


@router.get("")
async def list_scenarios(user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    rows = (await db.execute(select(Scenario).where(Scenario.user_id == user.id, Scenario.status != "done")
                             .order_by(Scenario.starts_at.is_(None), Scenario.starts_at, Scenario.created_at.desc()))).scalars()
    out: dict[str, list] = {"upcoming": [], "recurring": [], "mine": []}
    for s in rows:
        out["mine" if s.kind == "manual" else s.kind].append(await serialise(db, s))
    return out


@router.post("", dependencies=[limit("coach", "coach_rate_limit_per_minute")])
async def create(body: ScenarioIn, request: Request, user: User = Depends(current_user),
                 db: AsyncSession = Depends(get_session)) -> dict:
    s = Scenario(user_id=user.id, title=body.title.strip(), kind=body.kind, starts_at=_aware(body.starts_at))
    db.add(s)
    await db.commit()
    await prepare(db, request.app.state.agents, s)
    return await serialise(db, s, with_phrases=True)


@router.post("/calendar", dependencies=[limit("coach", "coach_rate_limit_per_minute")])
async def from_calendar(body: CalendarIn, request: Request, user: User = Depends(current_user),
                        db: AsyncSession = Depends(get_session)) -> dict:
    now = utcnow()
    existing = {(s.title, s.starts_at) for s in (await db.execute(
        select(Scenario).where(Scenario.user_id == user.id, Scenario.kind == "upcoming"))).scalars()}
    created = []
    for e in body.events:
        starts = _aware(e.starts_at)
        if not (now <= starts <= now + CALENDAR_HORIZON) or (e.title.strip(), starts) in existing:
            continue
        s = Scenario(user_id=user.id, title=e.title.strip(), kind="upcoming", starts_at=starts)
        db.add(s)
        await db.commit()
        await prepare(db, request.app.state.agents, s)
        created.append(await serialise(db, s))
    return {"created": created}


@router.get("/{scenario_id}")
async def detail(scenario_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    return await serialise(db, await _owned(db, user.id, scenario_id), with_phrases=True)


@router.patch("/{scenario_id}")
async def set_status(scenario_id: str, body: StatusIn, request: Request, user: User = Depends(current_user),
                     db: AsyncSession = Depends(get_session)) -> dict:
    s = await _owned(db, user.id, scenario_id)
    s.status = body.status
    await db.commit()
    has_pack = (await db.execute(select(ScenarioPhrase.id).where(ScenarioPhrase.scenario_id == s.id).limit(1))).first()
    if body.status == "active" and not has_pack:  # accepting a suggested recurring scene
        await prepare(db, request.app.state.agents, s)
    return await serialise(db, s, with_phrases=True)


@router.post("/{scenario_id}/readiness")
async def rate(scenario_id: str, body: ReadinessIn, user: User = Depends(current_user),
               db: AsyncSession = Depends(get_session)) -> dict:
    s = await _owned(db, user.id, scenario_id)
    db.add(Readiness(user_id=user.id, scenario_id=s.id, value=body.value, phase=body.phase))
    await db.commit()
    return (await serialise(db, s))["readiness"]
