import pytest

from app.curation.level import estimate, reflection_line

pytestmark = pytest.mark.anyio


def test_level_estimate_leans_on_words_kept():
    assert estimate(0, None, None)["band"] == "Pre-A1"
    assert estimate(160, 0.6, 5.0)["band"] == "A2"
    assert estimate(1000, 0.95, 11.0)["level"] >= 4


def test_reflection_line_is_specific_and_calm():
    assert reflection_line(0, None, None, 0, 0).startswith("A quiet week")
    assert reflection_line(12, 0.6, 0.4, 5, 1) == "More of your sentences were Spanish than the week before (60%), you rehearsed 1 scene and 5 words stuck."


async def test_lessons_follow_what_you_said(client, auth):
    await client.post("/v1/coach", json={"text": "I want you to call me tomorrow"}, headers=auth)
    await client.post("/v1/coach", json={"text": "there is a problem with the car"}, headers=auth)
    mine = (await client.get("/v1/lessons", headers=auth)).json()["lessons"]
    assert {m["id"] for m in mine} >= {"subjunctive_want", "hay"}
    assert next(m for m in mine if m["id"] == "hay")["you_said"] == "there is a problem with the car"

    lesson = (await client.get("/v1/lessons/subjunctive_want", headers=auth)).json()
    assert lesson["title"] and len(lesson["examples"]) == 3 and lesson["check"]["answer"] in range(3)
    assert (await client.get("/v1/lessons/nope", headers=auth)).status_code == 404


async def test_progress_has_level_and_reflection(client, auth):
    await client.post("/v1/coach", json={"text": "quiero practicar mi español"}, headers=auth)
    p = (await client.get("/v1/progress", headers=auth)).json()
    assert p["level_estimate"]["band"] in {"Pre-A1", "A1"} and p["level_estimate"]["current_setting"] == 0
    assert p["reflection"]["sentences"] == 1 and p["reflection"]["line"].endswith(".")
