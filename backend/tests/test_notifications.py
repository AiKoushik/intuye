from datetime import datetime, timedelta, timezone

import pytest

from app.curation.notify import SceneIn, plan

pytestmark = pytest.mark.anyio
UTC = timezone.utc


def test_plan_keeps_budget_quiet_hours_and_gap():
    now = datetime(2026, 11, 16, 8, 0, tzinfo=UTC)  # a Monday, 08:00 in UTC
    dentist = SceneIn("s1", "At the dentist", datetime(2026, 11, 17, 10, 0, tzinfo=UTC), 10, 3)
    sent, dropped = plan(now, "UTC", 2, "22:00", "08:00", [dentist], lambda at: 12, days=3)
    kinds = [(c.kind, c.fire_at.strftime("%a %H:%M")) for c in sent]
    assert ("scene_eve", "Mon 19:00") in kinds and ("scene_soon", "Tue 08:00") in kinds
    per_day = {}
    for c in sent:
        per_day[c.fire_at.date()] = per_day.get(c.fire_at.date(), 0) + 1
    assert max(per_day.values()) <= 2
    assert all(b.fire_at - a.fire_at >= timedelta(hours=1) for a, b in zip(sent, sent[1:]))
    assert any(d["reason"] == "daily limit" for d in dropped)
    assert all(c.why for c in sent)


def test_scene_reminder_in_quiet_hours_moves_earlier():
    now = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
    early = SceneIn("s2", "Job interview", datetime(2026, 11, 17, 7, 0, tzinfo=UTC), 9, 3)  # 2 h before = 05:00, quiet
    sent, _ = plan(now, "UTC", 3, "22:00", "08:00", [early], lambda at: 0, days=2)
    soon = next(c for c in sent if c.kind == "scene_soon")
    assert soon.fire_at == datetime(2026, 11, 16, 21, 30, tzinfo=UTC)


async def test_plan_endpoint_and_offline_review_replay(client, auth):
    await client.post("/v1/coach", json={"text": "me gusta escuchar este en mi mind"}, headers=auth)
    items = (await client.post("/v1/batches/next", json={"size": 7}, headers=auth)).json()["items"]
    p = (await client.get("/v1/notifications/plan?tz=Europe/Madrid", headers=auth)).json()
    assert p["timezone"] == "Europe/Madrid" and p["budget"] == 3
    assert any(n["kind"] == "review" for n in p["notifications"])

    lx = items[0]["lexeme_id"]
    earlier = (datetime.now(UTC) - timedelta(hours=3)).isoformat()
    later = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    r = (await client.post("/v1/reviews", json={"lexeme_id": lx, "rating": 3, "reviewed_at": later}, headers=auth)).json()
    assert r["state"] == "review"
    stale = (await client.post("/v1/reviews", json={"lexeme_id": lx, "rating": 1, "reviewed_at": earlier}, headers=auth)).json()
    assert stale["replayed"] is False and stale["state"] == "review"
