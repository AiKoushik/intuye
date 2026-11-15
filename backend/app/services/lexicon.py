"""Lexeme bookkeeping shared by coach, capture, scenarios and curation. Every query is user- and language-scoped."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.curation.text import is_target_token, normalize_entry, tokens
from app.languages import LanguagePack, default_variety, for_variety
from app.models import Card, Lexeme, LexemeEvent, UserSettings, utcnow


async def learner_language(db: AsyncSession, user_id: str) -> tuple[LanguagePack, str]:
    """The language pack and variety the learner is on now (from their variety setting)."""
    s = await db.get(UserSettings, user_id)
    variety = s.dialect if s else default_variety()
    return for_variety(variety), variety


def candidates_from_alignment(alignment: list[dict], to_target: bool, pack: LanguagePack) -> list[tuple[str, str]]:
    """(target, en) pairs worth tracking: target-language words the learner needed but didn't produce themselves."""
    out: list[tuple[str, str]] = []
    for p in alignment:
        src, tgt = p.get("src", ""), p.get("tgt", "")
        if to_target:
            src_toks = tokens(src, pack)
            if not src_toks or all(is_target_token(t, pack) for t in src_toks):
                continue  # already said in the target language
            target, en = normalize_entry(tgt, pack), src.strip().lower()
        else:
            target, en = normalize_entry(src, pack), tgt.strip().lower().rstrip("?.!")
        if target and target not in pack.stopwords and len(target) <= 60:
            out.append((target, en[:120]))
    return out


async def known_target(db: AsyncSession, user_id: str, pack: LanguagePack) -> set[str]:
    rows = await db.execute(select(Lexeme.target).join(Card, Card.lexeme_id == Lexeme.id)
                            .where(Lexeme.user_id == user_id, Lexeme.lang == pack.code, Card.reps > 0))
    return set(rows.scalars())


async def upsert_lexeme(db: AsyncSession, user_id: str, target: str, en: str, origin: str, *, pack: LanguagePack,
                        topic: str | None = None, context: str | None = None) -> Lexeme:
    target = normalize_entry(target, pack)
    row = (await db.execute(select(Lexeme).where(Lexeme.user_id == user_id, Lexeme.lang == pack.code,
                                                 Lexeme.target == target))).scalar_one_or_none()
    if row is None:
        row = Lexeme(user_id=user_id, lang=pack.code, target=target, en=en[:120], origin=origin, topic=topic,
                     context=(context or "")[:500] or None)
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
