"""Lexeme bookkeeping shared by coach, capture, scenarios and curation. Every query is user-scoped."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.curation.text import is_spanish_token, normalize_es, tokens
from app.models import Card, Lexeme, LexemeEvent, utcnow

STOP_ES = {"el", "la", "los", "las", "un", "una", "de", "y", "a", "en", "que", "yo", "mi", "me", "te", "se", "lo", "es"}


def candidates_from_alignment(alignment: list[dict], to_es: bool) -> list[tuple[str, str]]:
    """(es, en) pairs worth tracking: Spanish the learner needed but didn't produce themselves."""
    out: list[tuple[str, str]] = []
    for p in alignment:
        src, tgt = p.get("src", ""), p.get("tgt", "")
        if to_es:
            src_toks = tokens(src)
            if not src_toks or all(is_spanish_token(t) for t in src_toks):
                continue  # already said in Spanish
            es, en = normalize_es(tgt), src.strip().lower()
        else:
            es, en = normalize_es(src), tgt.strip().lower().rstrip("?.!")
        if es and es not in STOP_ES and len(es) <= 60:
            out.append((es, en[:120]))
    return out


async def known_es(db: AsyncSession, user_id: str) -> set[str]:
    rows = await db.execute(select(Lexeme.es).join(Card, Card.lexeme_id == Lexeme.id)
                            .where(Lexeme.user_id == user_id, Card.reps > 0))
    return set(rows.scalars())


async def upsert_lexeme(db: AsyncSession, user_id: str, es: str, en: str, origin: str, topic: str | None = None,
                        context: str | None = None) -> Lexeme:
    es = normalize_es(es)
    row = (await db.execute(select(Lexeme).where(Lexeme.user_id == user_id, Lexeme.es == es))).scalar_one_or_none()
    if row is None:
        row = Lexeme(user_id=user_id, es=es, en=en[:120], origin=origin, topic=topic, context=(context or "")[:500] or None)
        db.add(row)
        await db.flush()
    else:
        if topic and not row.topic:
            row.topic = topic
        if context and not row.context:
            row.context = context[:500]
    return row


async def record_event(db: AsyncSession, user_id: str, lexeme_id: str, kind: str, utterance_id: str | None = None,
                       at: datetime | None = None) -> None:
    db.add(LexemeEvent(user_id=user_id, lexeme_id=lexeme_id, kind=kind, utterance_id=utterance_id, at=at or utcnow()))
