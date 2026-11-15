"""Grammar on demand: the lessons your own sentences triggered, and each 60-second lesson."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.curation import grammar
from app.curation.lessons import lesson
from app.services.lexicon import learner_language
from app.db import get_session
from app.errors import APIError
from app.models import User, Utterance, utcnow
from app.security.deps import current_user

router = APIRouter(prefix="/v1/lessons", tags=["lessons"])


@router.get("")
async def mine(user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    """Lessons triggered by things you said in the last 30 days, with the sentence that triggered each."""
    since = utcnow() - timedelta(days=30)
    pack, _ = await learner_language(db, user.id)
    seen: dict[str, str] = {}
    for u in (await db.execute(select(Utterance).where(Utterance.user_id == user.id, Utterance.lang == pack.code,
                                                       Utterance.spoken_at >= since)
                               .order_by(Utterance.spoken_at.desc()).limit(300))).scalars():
        for t in grammar.matches(u.text, pack):
            seen.setdefault(t.id, u.text)
    return {"lessons": [{"id": k, "title": pack.lessons[k].title, "pattern": pack.lessons[k].pattern, "you_said": v}
                        for k, v in seen.items() if k in pack.lessons]}


@router.get("/{lesson_id}")
async def one(lesson_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    pack, _ = await learner_language(db, user.id)
    data = lesson(lesson_id, pack)
    if data is None:
        raise APIError(404, "not_found", "There's no lesson with that name.")
    return data
