from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.curation.text import english_share
from app.db import get_session
from app.models import User, Utterance
from app.security.deps import current_user, limit
from app.services.lexicon import candidates_from_alignment, known_target, learner_language, record_event, upsert_lexeme

router = APIRouter(prefix="/v1", tags=["coach"])


class CoachIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    direction: Literal["auto", "to_target", "to_native"] = "auto"


class Pair(BaseModel):
    src: str
    tgt: str
    new: bool


class CoachOut(BaseModel):
    intent: Literal["to_target", "to_native", "ask"]
    source: str
    close: str
    natural: str | None
    alignment: list[Pair]
    answer: str | None
    utterance_id: str | None


@router.post("/coach", response_model=CoachOut, dependencies=[limit("coach", "coach_rate_limit_per_minute")])
async def coach(body: CoachIn, request: Request, user: User = Depends(current_user),
                db: AsyncSession = Depends(get_session)) -> CoachOut:
    pack, variety = await learner_language(db, user.id)
    known = await known_target(db, user.id, pack)
    state = await request.app.state.agents.coach.ainvoke(
        {"text": body.text, "direction": body.direction, "dialect": variety, "known": known})

    utterance_id = None
    if state["intent"] != "ask":
        to_target = state["intent"] == "to_target"
        u = Utterance(user_id=user.id, lang=pack.code, text=body.text, source="say", lang_mix=english_share(state["payload"], pack),
                      close_target=state["close"] if to_target else state["payload"])
        db.add(u)
        await db.flush()
        utterance_id = u.id
        for target, en in candidates_from_alignment(state["alignment"], to_target, pack):
            lex = await upsert_lexeme(db, user.id, target, en, origin="spoken", pack=pack,
                                      context=state["close"] if to_target else state["payload"])
            await record_event(db, user.id, lex.id, "looked_up", u.id)
        await db.commit()

    return CoachOut(intent=state["intent"], source=state["payload"], close=state.get("close") or "",
                    natural=state.get("natural"), alignment=state.get("alignment") or [], answer=state.get("answer"),
                    utterance_id=utterance_id)
