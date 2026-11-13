from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import rehearse
from app.agents.runtime import AgentContext
from app.curation.text import english_share
from app.db import get_session
from app.errors import APIError
from app.models import Rehearsal, RehearsalTurn, Scenario, User, UserSettings, Utterance, utcnow
from app.security.deps import current_user, limit

router = APIRouter(prefix="/v1/rehearsals", tags=["rehearse"], dependencies=[limit("coach", "coach_rate_limit_per_minute")])


class StartIn(BaseModel):
    scenario_id: str = Field(min_length=36, max_length=36)
    difficulty: Literal["gentle", "real", "fast"] = "gentle"


class TurnIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)


async def _owned(db: AsyncSession, user_id: str, rehearsal_id: str) -> tuple[Rehearsal, Scenario]:
    row = (await db.execute(select(Rehearsal, Scenario).join(Scenario, Scenario.id == Rehearsal.scenario_id)
                            .where(Rehearsal.id == rehearsal_id, Rehearsal.user_id == user_id))).first()
    if row is None:
        raise APIError(404, "not_found", "That rehearsal doesn't exist.")
    return row[0], row[1]


async def _dialect(db: AsyncSession, user_id: str) -> str:
    s = await db.get(UserSettings, user_id)
    return s.dialect if s else "es-419"


async def _ctx(db: AsyncSession, user_id: str, title: str, difficulty: str) -> AgentContext:
    return AgentContext(dialect=await _dialect(db, user_id), title=title, difficulty=difficulty)


@router.post("")
async def start(body: StartIn, request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    scen = (await db.execute(select(Scenario).where(Scenario.id == body.scenario_id, Scenario.user_id == user.id))).scalar_one_or_none()
    if scen is None:
        raise APIError(404, "not_found", "That scene doesn't exist.")
    r = Rehearsal(user_id=user.id, scenario_id=scen.id, difficulty=body.difficulty)
    db.add(r)
    await db.flush()
    coach = await rehearse.opening(request.app.state.agents, r.id, await _ctx(db, user.id, scen.title, body.difficulty))
    db.add(RehearsalTurn(rehearsal_id=r.id, role="coach", text=coach.reply_es, en=coach.reply_en))
    await db.commit()
    return {"rehearsal_id": r.id, "coach": {"es": coach.reply_es, "en": coach.reply_en}}


@router.post("/{rehearsal_id}/turns")
async def turn(rehearsal_id: str, body: TurnIn, request: Request, user: User = Depends(current_user),
               db: AsyncSession = Depends(get_session)) -> dict:
    r, scen = await _owned(db, user.id, rehearsal_id)
    if r.ended_at:
        raise APIError(409, "ended", "This rehearsal has ended.")
    history = [{"role": t.role, "text": t.text} for t in (await db.execute(
        select(RehearsalTurn).where(RehearsalTurn.rehearsal_id == r.id).order_by(RehearsalTurn.at))).scalars()]
    native, coach, done = await rehearse.turn(request.app.state.agents, r.id, await _ctx(db, user.id, scen.title, r.difficulty),
                                              body.text, history)
    db.add(RehearsalTurn(rehearsal_id=r.id, role="user", text=body.text, native=native))
    db.add(RehearsalTurn(rehearsal_id=r.id, role="coach", text=coach.reply_es, en=coach.reply_en))
    db.add(Utterance(user_id=user.id, text=body.text, source="rehearsal", lang_mix=english_share(body.text),
                     close_es=native or body.text))
    await db.commit()
    return {"native": native, "coach": {"es": coach.reply_es, "en": coach.reply_en}, "done": done}


@router.post("/{rehearsal_id}/end")
async def end(rehearsal_id: str, request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    r, scen = await _owned(db, user.id, rehearsal_id)
    turns = [{"role": t.role, "text": t.text} for t in (await db.execute(
        select(RehearsalTurn).where(RehearsalTurn.rehearsal_id == r.id).order_by(RehearsalTurn.at))).scalars()]
    out = await rehearse.summarise(request.app.state.agents, await _ctx(db, user.id, scen.title, r.difficulty), turns)
    r.ended_at, r.summary = utcnow(), out.went_well
    await db.commit()
    return {"summary": out.went_well, "keep_phrases": [p.model_dump() for p in out.keep]}
