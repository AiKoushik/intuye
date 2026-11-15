from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.curation.lessons import lesson_id_for
from app.curation import fsrs
from app.db import get_session
from app.errors import APIError
from app.models import Batch, BatchItem, Card, Lexeme, LexemeEvent, Review, User, utcnow
from app.security.deps import current_user
from app.services.curation import build_batch, to_state

router = APIRouter(prefix="/v1", tags=["words"])


class BatchIn(BaseModel):
    size: int = Field(default=7, ge=5, le=10)


class ReviewIn(BaseModel):
    lexeme_id: str = Field(min_length=36, max_length=36)
    rating: int = Field(ge=1, le=4)
    # Set when a review done offline is replayed later; scheduling uses the moment it actually happened.
    reviewed_at: datetime | None = None

OFFLINE_WINDOW = timedelta(days=14)


@router.post("/batches/next")
async def next_batch(body: BatchIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    batch, picks = await build_batch(db, user.id, body.size)
    return {"batch_id": batch.id, "items": [
        {"lexeme_id": lx.id, "es": lx.es, "en": lx.en, "reason": p.reason, "reason_kind": p.reason_kind, "lesson_id": lesson_id_for(lx.es),
         "context": lx.context} for p, lx in picks]}


@router.get("/reviews/due")
async def due(user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    now = utcnow()
    rows = (await db.execute(select(Card, Lexeme).join(Lexeme, Lexeme.id == Card.lexeme_id).where(
        Card.user_id == user.id, Card.due_at <= now).order_by(Card.due_at).limit(50))).all()
    reasons = {}
    if rows:
        ids = [lx.id for _, lx in rows]
        for item in (await db.execute(select(BatchItem).join(Batch).where(
                Batch.user_id == user.id, BatchItem.lexeme_id.in_(ids)).order_by(Batch.created_at))).scalars():
            reasons[item.lexeme_id] = (item.reason, item.reason_kind)
    return {"items": [{"lexeme_id": lx.id, "es": lx.es, "en": lx.en, "context": lx.context, "state": c.state,
                       "reason": reasons.get(lx.id, (None, None))[0], "reason_kind": reasons.get(lx.id, (None, lx.origin))[1],
                       "lesson_id": lesson_id_for(lx.es)}
                      for c, lx in rows]}


@router.post("/reviews")
async def review(body: ReviewIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    card = (await db.execute(select(Card).where(Card.lexeme_id == body.lexeme_id, Card.user_id == user.id))).scalar_one_or_none()
    if card is None:
        raise APIError(404, "not_found", "That word isn't in your reviews.")
    now = utcnow()
    if body.reviewed_at is not None:
        at = body.reviewed_at if body.reviewed_at.tzinfo else body.reviewed_at.replace(tzinfo=timezone.utc)
        if card.last_review_at and at <= card.last_review_at:
            # Already superseded by a later review (e.g. the same card reviewed on another device): keep the newer one.
            return {"due_at": card.due_at.isoformat() if card.due_at else None, "scheduled_days": 0, "state": card.state, "replayed": False}
        now = min(max(at, now - OFFLINE_WINDOW), now)
    result = fsrs.schedule(to_state(card), body.rating, now)
    nc = result.card
    card.state, card.stability, card.difficulty = nc.state, nc.stability, nc.difficulty
    card.reps, card.lapses, card.last_review_at, card.due_at = nc.reps, nc.lapses, nc.last_review_at, nc.due_at
    db.add(Review(user_id=user.id, lexeme_id=card.lexeme_id, rating=body.rating, elapsed_days=result.elapsed_days,
                  scheduled_days=result.scheduled_days, retrievability=result.retrievability, reviewed_at=now))
    if body.rating == fsrs.AGAIN:
        db.add(LexemeEvent(user_id=user.id, lexeme_id=card.lexeme_id, kind="forgot", at=now))
    await _maybe_complete_batches(db, user.id)
    await db.commit()
    return {"due_at": nc.due_at.isoformat() if nc.due_at else None, "scheduled_days": result.scheduled_days, "state": nc.state}


async def _maybe_complete_batches(db: AsyncSession, user_id: str) -> None:
    open_batches = (await db.execute(select(Batch).where(Batch.user_id == user_id, Batch.completed_at.is_(None)))).scalars()
    for b in open_batches:
        pending = (await db.execute(select(Card.lexeme_id).join(BatchItem, BatchItem.lexeme_id == Card.lexeme_id).where(
            BatchItem.batch_id == b.id, Card.reps == 0))).first()
        if pending is None:
            b.completed_at = utcnow()
