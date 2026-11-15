"""The notification plan clients schedule locally (iPhone) or show (web)."""
from __future__ import annotations

from datetime import timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.curation import notify
from app.db import get_session
from app.models import Card, Scenario, ScenarioPhrase, User, UserSettings, utcnow
from app.security.deps import current_user

router = APIRouter(prefix="/v1/notifications", tags=["notifications"])


@router.get("/plan")
async def plan(days: int = Query(default=7, ge=1, le=14), tz: str | None = Query(default=None, max_length=64),
               user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    now = utcnow()
    settings = await db.get(UserSettings, user.id)
    zone = settings.timezone if settings else "UTC"
    if tz and tz != zone:
        try:
            ZoneInfo(tz)
            zone = tz
            if settings:
                settings.timezone = tz
                await db.commit()
        except (ZoneInfoNotFoundError, ValueError):
            pass

    scenes = []
    for s in (await db.execute(select(Scenario).where(Scenario.user_id == user.id, Scenario.status == "active",
                                                      Scenario.starts_at > now, Scenario.starts_at <= now + timedelta(days=days + 1)))).scalars():
        counts = dict((await db.execute(select(ScenarioPhrase.kind, func.count()).where(ScenarioPhrase.scenario_id == s.id)
                                        .group_by(ScenarioPhrase.kind))).all())
        scenes.append(notify.SceneIn(s.id, s.title, s.starts_at, counts.get("key", 0) + counts.get("rescue", 0), counts.get("rescue", 0)))

    dues = sorted(d for (d,) in (await db.execute(select(Card.due_at).where(Card.user_id == user.id))).all())
    def due_by(at):
        return sum(1 for d in dues if d <= at)

    budget = settings.daily_notification_budget if settings else 3
    sent, dropped = notify.plan(now, zone, budget, settings.quiet_start if settings else "22:00",
                                settings.quiet_end if settings else "08:00", scenes, due_by, days)
    z = ZoneInfo(zone)
    return {"timezone": zone, "budget": budget,
            "notifications": [{"id": c.id, "kind": c.kind, "fire_at": c.fire_at.astimezone(ZoneInfo("UTC")).isoformat(),
                               "local": c.fire_at.astimezone(z).strftime("%a %H:%M"), "title": c.title, "body": c.body, "why": c.why,
                               "scenario_id": c.scenario_id} for c in sent],
            "suppressed": dropped}
