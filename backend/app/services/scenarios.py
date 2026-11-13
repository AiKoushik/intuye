from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime import AgentContext
from app.agents.scene_builder import build_scene
from app.agents.schemas import PrepPackOut, SceneCardOut
from app.models import Readiness, Scenario, ScenarioPhrase, UserSettings
from app.services.lexicon import upsert_lexeme


async def context_for(db: AsyncSession, user_id: str, title: str = "") -> AgentContext:
    settings = await db.get(UserSettings, user_id)
    return AgentContext(dialect=settings.dialect if settings else "es-419", level=settings.level if settings else 0, title=title)


async def prepare(db: AsyncSession, agents, scenario: Scenario, ctx: AgentContext | None = None) -> tuple[PrepPackOut, SceneCardOut]:
    """Run the scene builder agent and store the pack; key phrases become lexemes tied to the scene."""
    ctx = ctx or await context_for(db, scenario.user_id, scenario.title)
    pack, card = await build_scene(agents, ctx, scenario.title, scenario.details)
    scenario.topic = scenario.topic or card.topic.strip().lower()[:64] or None
    await store_pack(db, scenario, pack.model_dump())
    return pack, card


async def store_pack(db: AsyncSession, scenario: Scenario, pack: dict) -> None:
    for kind in ("key", "rescue", "hear"):
        for pos, p in enumerate(pack[kind]):
            db.add(ScenarioPhrase(scenario_id=scenario.id, kind=kind, en=p["en"][:300], es=p["es"][:300],
                                  alignment=p.get("alignment") or [], position=pos))
            if kind == "key":
                await upsert_lexeme(db, scenario.user_id, p["es"], p["en"], origin="scenario", topic=f"scene:{scenario.id}",
                                    context=p["es"])
    await db.commit()


async def serialise(db: AsyncSession, s: Scenario, with_phrases: bool = False) -> dict:
    ratings = list((await db.execute(select(Readiness).where(Readiness.scenario_id == s.id).order_by(Readiness.at))).scalars())
    before = next((r.value for r in ratings if r.phase == "before"), None)
    after = next((r.value for r in reversed(ratings) if r.phase == "after"), None)
    out = {"id": s.id, "title": s.title, "details": s.details, "kind": s.kind, "topic": s.topic, "status": s.status,
           "template_id": s.template_id,
           "starts_at": s.starts_at.isoformat() if s.starts_at else None,
           "readiness": {"before": before, "after": after, "current": after or before}}
    if with_phrases:
        phrases = (await db.execute(select(ScenarioPhrase).where(ScenarioPhrase.scenario_id == s.id)
                                    .order_by(ScenarioPhrase.kind, ScenarioPhrase.position))).scalars()
        grouped: dict[str, list] = {"key": [], "rescue": [], "hear": []}
        for p in phrases:
            grouped[p.kind].append({"id": p.id, "en": p.en, "es": p.es, "alignment": p.alignment})
        out["phrases"] = grouped
    return out
