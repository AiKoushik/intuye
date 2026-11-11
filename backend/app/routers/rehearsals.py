from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.rehearse import summarise
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


def _config(rehearsal_id: str) -> dict:
    return {"configurable": {"thread_id": rehearsal_id}}


@router.post("")
async def start(body: StartIn, request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    scen = (await db.execute(select(Scenario).where(Scenario.id == body.scenario_id, Scenario.user_id == user.id))).scalar_one_or_none()
    if scen is None:
        raise APIError(404, "not_found", "That scene doesn't exist.")
    r = Rehearsal(user_id=user.id, scenario_id=scen.id, difficulty=body.difficulty)
    db.add(r)
    await db.flush()
    state = await request.app.state.graphs.rehearse.ainvoke(
        {"title": scen.title, "dialect": await _dialect(db, user.id), "difficulty": body.difficulty, "turns": [],
         "user_text": None}, _config(r.id))
    coach = state["last"]
    db.add(RehearsalTurn(rehearsal_id=r.id, role="coach", text=coach["text"], en=coach["en"]))
    await db.commit()
    return {"rehearsal_id": r.id, "coach": {"es": coach["text"], "en": coach["en"]}}


@router.post("/{rehearsal_id}/turns")
async def turn(rehearsal_id: str, body: TurnIn, request: Request, user: User = Depends(current_user),
               db: AsyncSession = Depends(get_session)) -> dict:
    r, scen = await _owned(db, user.id, rehearsal_id)
    if r.ended_at:
        raise APIError(409, "ended", "This rehearsal has ended.")
    graph = request.app.state.graphs.rehearse
    snapshot = await graph.aget_state(_config(r.id))
    seed: dict = {"user_text": body.text}
    if not snapshot.values:  # checkpoint lost (restart): rebuild from the durable transcript
        turns = (await db.execute(select(RehearsalTurn).where(RehearsalTurn.rehearsal_id == r.id).order_by(RehearsalTurn.at))).scalars()
        seed |= {"title": scen.title, "dialect": await _dialect(db, user.id), "difficulty": r.difficulty,
                 "turns": [{"role": t.role, "text": t.text, "en": t.en, "native": t.native} for t in turns]}
    state = await graph.ainvoke(seed, _config(r.id))
    user_turn, coach = state["turns"][-2], state["turns"][-1]
    db.add(RehearsalTurn(rehearsal_id=r.id, role="user", text=body.text, native=user_turn.get("native")))
    db.add(RehearsalTurn(rehearsal_id=r.id, role="coach", text=coach["text"], en=coach["en"]))
    db.add(Utterance(user_id=user.id, text=body.text, source="rehearsal", lang_mix=english_share(body.text),
                     close_es=user_turn.get("native") or body.text))
    await db.commit()
    return {"native": user_turn.get("native"), "coach": {"es": coach["text"], "en": coach["en"]}, "done": state["done"]}


@router.post("/{rehearsal_id}/end")
async def end(rehearsal_id: str, request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    r, scen = await _owned(db, user.id, rehearsal_id)
    turns = [{"role": t.role, "text": t.text} for t in (await db.execute(
        select(RehearsalTurn).where(RehearsalTurn.rehearsal_id == r.id).order_by(RehearsalTurn.at))).scalars()]
    out = await summarise(request.app.state.graphs.llm, scen.title, await _dialect(db, user.id), turns)
    r.ended_at, r.summary = utcnow(), out.went_well
    await db.commit()
    return {"summary": out.went_well, "keep_phrases": [p.model_dump() for p in out.keep]}
