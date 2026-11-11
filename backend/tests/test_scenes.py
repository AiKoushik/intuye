from datetime import datetime, timedelta, timezone

import pytest

from app.curation.pronunciation import score

pytestmark = pytest.mark.anyio


def test_pronunciation_ignores_spelling_that_sounds_the_same():
    assert score("vaca", "baca") == 1.0
    assert score("hola", "ola") == 1.0
    assert score("muela", "mesa") < 0.7


async def test_scene_prep_rehearse_and_confidence(client, auth):
    starts = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    scene = (await client.post("/v1/scenarios", json={"title": "At the dentist", "starts_at": starts, "kind": "upcoming"},
                               headers=auth)).json()
    assert len(scene["phrases"]["key"]) >= 8 and len(scene["phrases"]["rescue"]) >= 3 and len(scene["phrases"]["hear"]) >= 3
    sid = scene["id"]
    await client.post(f"/v1/scenarios/{sid}/readiness", json={"value": 2, "phase": "before"}, headers=auth)

    # Scene phrases show up in the next batch with a scenario reason.
    batch = (await client.post("/v1/batches/next", json={"size": 7}, headers=auth)).json()
    assert batch["items"][0]["reason_kind"] == "scenario" and "dentist" in batch["items"][0]["reason"]

    start = (await client.post("/v1/rehearsals", json={"scenario_id": sid}, headers=auth)).json()
    rid = start["rehearsal_id"]
    assert start["coach"]["es"] and start["coach"]["en"]
    t1 = (await client.post(f"/v1/rehearsals/{rid}/turns", json={"text": "Me duele esta muela"}, headers=auth)).json()
    assert t1["native"] is None and t1["coach"]["es"]
    t2 = (await client.post(f"/v1/rehearsals/{rid}/turns", json={"text": "since yesterday"}, headers=auth)).json()
    assert t2["native"]  # English escape hatch gives the Spanish back
    end = (await client.post(f"/v1/rehearsals/{rid}/end", headers=auth)).json()
    assert end["summary"] and len(end["keep_phrases"]) == 3

    await client.post(f"/v1/scenarios/{sid}/readiness", json={"value": 4, "phase": "after"}, headers=auth)
    prog = (await client.get("/v1/progress", headers=auth)).json()
    assert prog["confidence"] == [{"scenario_id": sid, "title": "At the dentist", "before": 2, "after": 4}]
    assert prog["spanglish_ratio"] and prog["words"]["met"] >= 8

    today = (await client.get("/v1/today", headers=auth)).json()
    assert today["next_scenario"]["id"] == sid and today["words_ready"]["count"] >= 5


async def test_calendar_import_creates_upcoming_scene(client, auth):
    soon = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    far = (datetime.now(timezone.utc) + timedelta(days=40)).isoformat()
    r = (await client.post("/v1/scenarios/calendar", json={"events": [{"title": "Dentist", "starts_at": soon},
                                                                       {"title": "Conference", "starts_at": far}]},
                           headers=auth)).json()
    assert [s["title"] for s in r["created"]] == ["Dentist"]
    listed = (await client.get("/v1/scenarios", headers=auth)).json()
    assert [s["title"] for s in listed["upcoming"]] == ["Dentist"]


async def test_pronunciation_attempt_feeds_struggle(client, auth):
    await client.post("/v1/coach", json={"text": "my tooth"}, headers=auth)
    batch = (await client.post("/v1/batches/next", json={"size": 5}, headers=auth)).json()
    muela = next(i for i in batch["items"] if i["es"] == "muela")
    r = (await client.post("/v1/pronunciation", json={"lexeme_id": muela["lexeme_id"], "expected": "muela", "heard": "mesa"},
                           headers=auth)).json()
    assert r["ok"] is False
