import pytest

from app.agents.coach import route_input, trim_answer

pytestmark = pytest.mark.anyio


def test_router_intents():
    assert route_input("me gusta escuchar este en mi mind", "auto")[0] == "to_es"
    assert route_input("como te va", "auto")[0] == "to_en"
    assert route_input("what does como te va mean?", "auto") == ("to_en", "como te va")
    assert route_input("how do I say tooth in Spanish?", "auto") == ("to_es", "tooth")
    assert route_input("when do I use usted?", "auto")[0] == "ask"


def test_answer_is_trimmed_to_three_sentences():
    long = "One. Two. Three. Four. Five."
    assert trim_answer(long) == "One. Two. Three."


async def test_spanglish_to_spanish_close_and_new_word(client, auth):
    r = await client.post("/v1/coach", json={"text": "me gusta escuchar este en mi mind"}, headers=auth)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["intent"] == "to_es" and body["answer"] is None
    assert "\n" not in body["close"] and "mente" in body["close"].lower()
    new = {p["src"]: p["tgt"] for p in body["alignment"] if p["new"]}
    assert new == {"mind": "mente"}  # Spanish the learner already said isn't flagged


async def test_spanish_to_english_is_one_short_line(client, auth):
    r = await client.post("/v1/coach", json={"text": "como te va"}, headers=auth)
    body = r.json()
    assert body["intent"] == "to_en" and body["close"] == "How's it going?" and body["natural"] is None


async def test_explicit_question_gets_short_answer_only(client, auth):
    r = await client.post("/v1/coach", json={"text": "when do I use usted?"}, headers=auth)
    body = r.json()
    assert body["intent"] == "ask" and body["alignment"] == [] and body["close"] == ""
    assert body["answer"].count(".") <= 3 and len(body["answer"]) <= 320


async def test_ambient_ingest_tracks_words_and_suggests_recurring_scenario(client, auth):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    items = [{"text": t, "spoken_at": now, "source": "ambient"}
             for t in ("the brain is very interesting", "my brain hurts", "neuroscience is my work")]
    r = await client.post("/v1/utterances", json={"items": items}, headers=auth)
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["accepted"] == 3 and out["lexemes_touched"] >= 2
    assert [s["topic"] for s in out["suggested_scenarios"]] == ["neuroscience"]

    day = (await client.get("/v1/utterances", headers=auth)).json()
    assert len(day["items"]) == 3
    forgot = (await client.post("/v1/utterances/forget", json={"minutes": 10}, headers=auth)).json()
    assert forgot["deleted"] == 3
