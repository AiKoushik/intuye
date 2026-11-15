from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import APIError
from app.models import Scenario, User, Utterance, utcnow
from app.security.deps import current_user
from app.services.lexicon import learner_language, record_event, upsert_lexeme

router = APIRouter(prefix="/v1/utterances", tags=["capture"])

RECURRING_MIN = 3
RECURRING_WINDOW = timedelta(days=7)


class UtteranceIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    spoken_at: datetime
    source: Literal["ambient", "say", "rehearsal"] = "ambient"


class BatchIn(BaseModel):
    items: list[UtteranceIn] = Field(min_length=1, max_length=200)


class ForgetIn(BaseModel):
    minutes: int = Field(ge=1, le=24 * 60)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@router.post("")
async def ingest(body: BatchIn, request: Request, user: User = Depends(current_user),
                 db: AsyncSession = Depends(get_session)) -> dict:
    pack, variety = await learner_language(db, user.id)
    state = await request.app.state.agents.ingest.ainvoke({
        "items": [{"text": i.text, "spoken_at": _aware(i.spoken_at), "source": i.source} for i in body.items],
        "dialect": variety})

    touched: set[str] = set()
    for it in state["items"]:
        u = Utterance(user_id=user.id, lang=pack.code, text=it["text"], source=it["source"], lang_mix=it["lang_mix"],
                      topic=it.get("topic"), close_target=it.get("close_target"), spoken_at=it["spoken_at"])
        db.add(u)
        await db.flush()
        for target, en in it.get("candidates", []):
            lex = await upsert_lexeme(db, user.id, target, en, origin="spoken", pack=pack, topic=it.get("topic"),
                                      context=it.get("close_target"))
            await record_event(db, user.id, lex.id, "said_en", u.id, at=it["spoken_at"])
            touched.add(lex.id)
    await db.commit()
    suggested = await _detect_recurring(db, user.id, pack.code)
    return {"accepted": len(state["items"]), "lexemes_touched": len(touched), "suggested_scenarios": suggested}


async def _detect_recurring(db: AsyncSession, user_id: str, lang: str) -> list[dict]:
    since = utcnow() - RECURRING_WINDOW
    rows = await db.execute(select(Utterance.topic, func.count()).where(
        Utterance.user_id == user_id, Utterance.topic.is_not(None), Utterance.spoken_at >= since).group_by(Utterance.topic))
    existing = set((await db.execute(select(Scenario.topic).where(Scenario.user_id == user_id, Scenario.lang == lang,
                                                                  Scenario.topic.is_not(None)))).scalars())
    created = []
    for topic, count in rows.all():
        if count >= RECURRING_MIN and topic not in existing:
            s = Scenario(user_id=user_id, lang=lang, title=f"Talking about {topic}", kind="recurring", topic=topic, status="suggested")
            db.add(s)
            await db.flush()
            created.append({"id": s.id, "title": s.title, "topic": topic})
    await db.commit()
    return created


@router.get("")
async def moments(day: date | None = None, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    d = day or utcnow().date()
    start = datetime.combine(d, time.min, tzinfo=timezone.utc)
    rows = (await db.execute(select(Utterance).where(Utterance.user_id == user.id, Utterance.spoken_at >= start,
                                                     Utterance.spoken_at < start + timedelta(days=1))
                             .order_by(Utterance.spoken_at))).scalars()
    return {"day": d.isoformat(), "items": [{"id": u.id, "text": u.text, "close_target": u.close_target, "topic": u.topic,
                                             "source": u.source, "spoken_at": u.spoken_at.isoformat()} for u in rows]}


@router.post("/forget")
async def forget(body: ForgetIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    cutoff = utcnow() - timedelta(minutes=body.minutes)
    res = await db.execute(delete(Utterance).where(Utterance.user_id == user.id, Utterance.spoken_at >= cutoff))
    await db.commit()
    return {"deleted": res.rowcount}


@router.delete("/{utterance_id}", status_code=204)
async def remove(utterance_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> Response:
    res = await db.execute(delete(Utterance).where(Utterance.id == utterance_id, Utterance.user_id == user.id))
    await db.commit()
    if res.rowcount == 0:
        raise APIError(404, "not_found", "That moment doesn't exist.")
    return Response(status_code=204)
