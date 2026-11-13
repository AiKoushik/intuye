from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.curation.text import english_share
from app.db import get_session
from app.models import User, UserSettings, Utterance
from app.security.deps import current_user, limit
from app.services.lexicon import candidates_from_alignment, known_es, record_event, upsert_lexeme

router = APIRouter(prefix="/v1", tags=["coach"])


class CoachIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    direction: Literal["auto", "to_es", "to_en"] = "auto"


class Pair(BaseModel):
    src: str
    tgt: str
    new: bool


class CoachOut(BaseModel):
    intent: Literal["to_es", "to_en", "ask"]
    source: str
    close: str
    natural: str | None
    alignment: list[Pair]
    answer: str | None
    utterance_id: str | None


@router.post("/coach", response_model=CoachOut, dependencies=[limit("coach", "coach_rate_limit_per_minute")])
async def coach(body: CoachIn, request: Request, user: User = Depends(current_user),
                db: AsyncSession = Depends(get_session)) -> CoachOut:
    settings = await db.get(UserSettings, user.id)
    known = await known_es(db, user.id)
    state = await request.app.state.agents.coach.ainvoke(
        {"text": body.text, "direction": body.direction, "dialect": settings.dialect if settings else "es-419", "known": known})

    utterance_id = None
    if state["intent"] != "ask":
        to_es = state["intent"] == "to_es"
        u = Utterance(user_id=user.id, text=body.text, source="say", lang_mix=english_share(state["payload"]),
                      close_es=state["close"] if to_es else state["payload"])
        db.add(u)
        await db.flush()
        utterance_id = u.id
        for es, en in candidates_from_alignment(state["alignment"], to_es=to_es):
            lex = await upsert_lexeme(db, user.id, es, en, origin="spoken", context=state["close"] if to_es else state["payload"])
            await record_event(db, user.id, lex.id, "looked_up", u.id)
        await db.commit()

    return CoachOut(intent=state["intent"], source=state["payload"], close=state.get("close") or "",
                    natural=state.get("natural"), alignment=state.get("alignment") or [], answer=state.get("answer"),
                    utterance_id=utterance_id)
