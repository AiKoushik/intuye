"""Shared scene library: search by meaning, publish new scenes (de-duplicated), use and report."""
from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.schemas import PrepPackOut, SceneCardOut
from app.library.index import LibraryIndex, card_text
from app.models import LibraryReport, Scenario, SceneTemplate, User
from app.services.scenarios import store_pack
from app.languages import for_variety

MIN_SIMILARITY = 0.3
HIDE_AFTER_REPORTS = 3
# Emails, links, phone-like digit runs, long numbers: never published.
PERSONAL = re.compile(r"[\w.+-]+@[\w-]+\.\w|https?://|www\.|\+?\d[\d\s().-]{6,}\d|\b\d{5,}\b")
Credit = Literal["anonymous", "name"]


def has_personal_details(texts: list[str]) -> bool:
    return any(PERSONAL.search(t or "") for t in texts)


def phrases(t: SceneTemplate) -> dict:
    """The template's pack with language-neutral keys (rows saved before language packs used "es")."""
    return {kind: [{"en": p["en"], "target": p.get("target") or p.get("es", ""), "alignment": p.get("alignment") or []}
                   for p in t.pack.get(kind, [])] for kind in ("key", "rescue", "hear")}


def card(t: SceneTemplate, similarity: float | None = None) -> dict:
    out = {"id": t.id, "title": t.title, "situation": t.situation, "topic": t.topic, "uses": t.uses, "credit": t.credit_name}
    if similarity is not None:
        out["similarity"] = round(similarity, 3)
    return out


async def search(db: AsyncSession, index: LibraryIndex, dialect: str, q: str, limit: int = 10) -> list[dict]:
    q = " ".join(q.split())[:200]
    if not q:
        rows = (await db.execute(select(SceneTemplate).where(SceneTemplate.dialect == dialect, SceneTemplate.status == "published")
                                 .order_by(SceneTemplate.uses.desc(), SceneTemplate.created_at.desc()).limit(limit))).scalars()
        return [card(t) for t in rows]
    hits = [(i, s) for i, s in await index.nearest(db, dialect, await index.embed(q), k=limit * 3) if s >= MIN_SIMILARITY]
    if not hits:
        return []
    rows = {t.id: t for t in (await db.execute(select(SceneTemplate).where(SceneTemplate.id.in_([i for i, _ in hits])))).scalars()}
    scored = [(rows[i], s, s * (1 + 0.05 * math.log1p(rows[i].uses))) for i, s in hits if i in rows and rows[i].status == "published"]
    scored.sort(key=lambda x: -x[2])
    return [card(t, s) for t, s, _ in scored[:limit]]


def search_for_agent(sessionmaker, index: LibraryIndex, dialect: str):
    """The scene builder's `search_scene_library` tool runs this in its own session."""
    async def run(query: str) -> list[dict]:
        async with sessionmaker() as db:
            return await search(db, index, dialect, query, limit=3)
    return run


async def share(db: AsyncSession, index: LibraryIndex, user: User, scenario: Scenario, scene_card: SceneCardOut,
                pack: PrepPackOut, dialect: str, level: int, wanted: bool, credit: Credit, threshold: float) -> dict:
    """Publish the scene's generalised card and pack unless it's private, personal or already there."""
    if not wanted:
        return {"status": "private", "reason": "not_shared"}
    phrases = [p for kind in (pack.key, pack.rescue, pack.hear) for p in kind]
    if not scene_card.shareable or has_personal_details([scene_card.title, scene_card.situation]
                                                         + [p.target for p in phrases] + [p.en for p in phrases]):
        return {"status": "private", "reason": "personal"}
    vector = await index.embed(card_text(scene_card.title, scene_card.situation))
    nearest = await index.nearest(db, dialect, vector, k=1)
    if nearest and nearest[0][1] >= threshold:
        existing = await db.get(SceneTemplate, nearest[0][0])
        if existing is not None:
            existing.uses += 1
            scenario.template_id = existing.id
            await db.commit()
            return {"status": "already_in_library", "template": card(existing)}
    named = credit == "name" and bool(user.display_name)
    t = SceneTemplate(title=scene_card.title.strip()[:160], situation=scene_card.situation.strip()[:400],
                      topic=scene_card.topic.strip().lower()[:64] or None, dialect=dialect, level=level,
                      pack=pack.model_dump(), embedding=vector.tolist(), embed_model=index.embedder.model_id,
                      creator_user_id=user.id if named else None, credit_name=user.display_name if named else None)
    db.add(t)
    await db.flush()
    scenario.template_id = t.id
    await db.commit()
    return {"status": "shared", "template": card(t), "credit": "name" if named else "anonymous"}


async def use(db: AsyncSession, user: User, t: SceneTemplate, starts_at: datetime | None, kind: str) -> Scenario:
    s = Scenario(user_id=user.id, lang=for_variety(t.dialect).code, title=t.title, kind=kind, starts_at=starts_at, topic=t.topic,
                 template_id=t.id)
    db.add(s)
    await db.flush()
    t.uses += 1
    await store_pack(db, s, t.pack)
    return s


async def report(db: AsyncSession, user: User, t: SceneTemplate, reason: str) -> None:
    exists = (await db.execute(select(LibraryReport.id).where(LibraryReport.template_id == t.id,
                                                              LibraryReport.user_id == user.id))).first()
    if exists:
        return
    db.add(LibraryReport(template_id=t.id, user_id=user.id, reason=reason))
    t.reports += 1
    if t.reports >= HIDE_AFTER_REPORTS:
        t.status = "hidden"
    await db.commit()
