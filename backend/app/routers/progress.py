from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.curation import fsrs
from app.curation.phonemes import compare
from app.db import get_session
from app.errors import APIError
from app.models import (Card, Lexeme, LexemeEvent, PronunciationAttempt, Scenario, User, UserSettings, Utterance,
                        utcnow)
from app.security.deps import current_user
from app.services.scenarios import serialise

router = APIRouter(prefix="/v1", tags=["progress"])
MISPRONOUNCED_BELOW = 0.7


class PronunciationIn(BaseModel):
    lexeme_id: str = Field(min_length=36, max_length=36)
    expected: str = Field(min_length=1, max_length=300)
    heard: str = Field(min_length=0, max_length=300)


@router.post("/pronunciation")
async def pronounce(body: PronunciationIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    lx = (await db.execute(select(Lexeme).where(Lexeme.id == body.lexeme_id, Lexeme.user_id == user.id))).scalar_one_or_none()
    if lx is None:
        raise APIError(404, "not_found", "That word isn't in your list.")
    settings = await db.get(UserSettings, user.id)
    result = compare(body.expected, body.heard, settings.dialect if settings else "es-419")
    s = result["score"]
    db.add(PronunciationAttempt(user_id=user.id, lexeme_id=lx.id, expected=body.expected, heard=body.heard, score=s))
    if s < MISPRONOUNCED_BELOW:
        db.add(LexemeEvent(user_id=user.id, lexeme_id=lx.id, kind="mispronounced"))
    await db.commit()
    return {**result, "ok": s >= MISPRONOUNCED_BELOW}


@router.get("/progress")
async def progress(user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    now = utcnow()
    # Spanglish ratio: mean English share of sentences where the learner attempted Spanish, by ISO week.
    weekly: dict[str, list[float]] = defaultdict(list)
    for u in (await db.execute(select(Utterance).where(Utterance.user_id == user.id,
                                                       Utterance.spoken_at >= now - timedelta(weeks=8)))).scalars():
        if u.lang_mix < 0.9:
            y, w, _ = u.spoken_at.isocalendar()
            weekly[f"{y}-W{w:02d}"].append(u.lang_mix)
    ratio = [{"week": k, "ratio": round(sum(v) / len(v), 3), "sentences": len(v)} for k, v in sorted(weekly.items())]

    confidence = []
    for s in (await db.execute(select(Scenario).where(Scenario.user_id == user.id))).scalars():
        r = (await serialise(db, s))["readiness"]
        if r["before"] or r["after"]:
            confidence.append({"scenario_id": s.id, "title": s.title, "before": r["before"], "after": r["after"]})

    cards = list((await db.execute(select(Card).where(Card.user_id == user.id))).scalars())
    kept = sum(1 for c in cards if c.reps > 0 and c.last_review_at and
               fsrs.retrievability((now - c.last_review_at).total_seconds() / 86400, c.stability) >= 0.9)
    met = (await db.execute(select(func.count()).select_from(Lexeme).where(Lexeme.user_id == user.id))).scalar_one()
    due = sum(1 for c in cards if c.due_at <= now)
    return {"spanglish_ratio": ratio, "confidence": confidence, "words": {"met": met, "kept": kept, "due": due}}


@router.get("/today")
async def today(user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    now = utcnow()
    upcoming = (await db.execute(select(Scenario).where(Scenario.user_id == user.id, Scenario.status == "active",
                                                        Scenario.starts_at >= now).order_by(Scenario.starts_at).limit(1))).scalar_one_or_none()
    if upcoming is None:
        upcoming = (await db.execute(select(Scenario).where(Scenario.user_id == user.id, Scenario.status == "active")
                                     .order_by(Scenario.created_at.desc()).limit(1))).scalar_one_or_none()
    suggested = (await db.execute(select(func.count()).select_from(Scenario).where(
        Scenario.user_id == user.id, Scenario.status == "suggested"))).scalar_one()
    due_rows = (await db.execute(select(Lexeme.es, Lexeme.origin).join(Card, Card.lexeme_id == Lexeme.id).where(
        Card.user_id == user.id, Card.due_at <= now).order_by(Card.due_at).limit(50))).all()
    recent = (await db.execute(select(Utterance).where(Utterance.user_id == user.id, Utterance.source != "rehearsal")
                               .order_by(Utterance.spoken_at.desc()).limit(3))).scalars()
    return {"next_scenario": await serialise(db, upcoming) if upcoming else None, "suggested_scenarios": suggested,
            # preview_items carry where each word came from, so clients can tint it (spoken, scenario, base, grammar)
            "words_ready": {"count": len(due_rows), "preview": [r.es for r in due_rows[:4]],
                            "preview_items": [{"es": r.es, "origin": r.origin} for r in due_rows[:4]]},
            "recent": [{"id": u.id, "text": u.text, "close_es": u.close_es, "spoken_at": u.spoken_at.isoformat()} for u in recent]}
