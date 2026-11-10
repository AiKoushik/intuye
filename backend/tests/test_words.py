from datetime import datetime, timedelta, timezone

import pytest

from app.curation import fsrs
from app.curation.ranker import Candidate, select

pytestmark = pytest.mark.anyio


def test_fsrs_good_spaces_out_again_brings_back():
    now = datetime(2026, 11, 10, tzinfo=timezone.utc)
    first = fsrs.schedule(fsrs.CardState(), fsrs.GOOD, now)
    assert first.card.state == "review" and first.scheduled_days >= 3
    later = now + timedelta(days=first.scheduled_days)
    second = fsrs.schedule(first.card, fsrs.GOOD, later)
    assert second.scheduled_days > first.scheduled_days
    lapse = fsrs.schedule(second.card, fsrs.AGAIN, later + timedelta(days=second.scheduled_days))
    assert lapse.card.state == "relearning" and lapse.card.lapses == 1 and lapse.scheduled_days < 1


def test_ranker_prefers_spoken_words_and_gives_reasons():
    now = datetime(2026, 11, 10, tzinfo=timezone.utc)
    spoken = Candidate(key="1", es="mente", en="mind", origin="spoken", mentions=[now - timedelta(hours=h) for h in range(9)])
    base = [Candidate(key=f"b{i}", es=f"w{i}", en=f"w{i}", origin="base", base_rank=i + 20) for i in range(10)]
    picks = select([spoken, *base], now, level=1, topic_share={}, size=7)
    assert len(picks) == 7 and picks[0].candidate.es == "mente"
    assert picks[0].reason == "You said “mind” 9 times this week"
    assert all(p.reason for p in picks)


async def test_batch_then_review_flow(client, auth):
    await client.post("/v1/coach", json={"text": "me gusta escuchar este en mi mind"}, headers=auth)
    await client.post("/v1/coach", json={"text": "my mind is tired"}, headers=auth)

    batch = (await client.post("/v1/batches/next", json={"size": 7}, headers=auth)).json()
    items = batch["items"]
    assert 5 <= len(items) <= 7
    assert items[0]["es"] == "mente" and items[0]["reason_kind"] == "spoken"
    assert any(i["reason_kind"] == "base" for i in items)  # beginner gets backbone words too

    due = (await client.get("/v1/reviews/due", headers=auth)).json()["items"]
    assert {d["lexeme_id"] for d in due} >= {i["lexeme_id"] for i in items}

    r = await client.post("/v1/reviews", json={"lexeme_id": items[0]["lexeme_id"], "rating": 3}, headers=auth)
    assert r.status_code == 200 and r.json()["state"] == "review" and r.json()["scheduled_days"] >= 1
