import pytest

from tests.conftest import sign_in

pytestmark = pytest.mark.anyio


async def _user(client, apple, sub: str) -> dict:
    return {"authorization": f"Bearer {(await sign_in(client, apple, sub))['access_token']}"}


async def test_share_search_dedupe_and_use(client, auth, apple):
    a = (await client.post("/v1/scenarios", json={"title": "At the dentist", "details": "my molar hurts"}, headers=auth)).json()
    assert a["library"]["status"] == "shared" and a["library"]["credit"] == "anonymous"
    tid = a["library"]["template"]["id"]

    b = await _user(client, apple, "apple-user-2")
    hits = (await client.get("/v1/library", params={"q": "going to the dentist's"}, headers=b)).json()["results"]
    assert hits[0]["id"] == tid and hits[0]["credit"] is None and hits[0]["similarity"] > 0.8

    # Same scene built again: nothing new in the library; the learner's scene links to the existing one.
    dup = (await client.post("/v1/scenarios", json={"title": "At the dentist's"}, headers=b)).json()
    assert dup["library"]["status"] == "already_in_library" and dup["template_id"] == tid
    assert len(dup["phrases"]["key"]) >= 8

    used = (await client.post(f"/v1/library/{tid}/use", json={}, headers=b)).json()
    assert used["template_id"] == tid and len(used["phrases"]["key"]) >= 8 and used["title"] == "At the dentist"
    detail = (await client.get(f"/v1/library/{tid}", headers=b)).json()
    assert detail["uses"] == 3 and len(detail["phrases"]["rescue"]) >= 3


async def test_credit_is_removed_when_the_creator_deletes_their_account(client, auth, apple):
    r = (await client.post("/v1/scenarios", json={"title": "Ordering food", "credit": "name"}, headers=auth)).json()
    assert r["library"]["credit"] == "name"
    other = await _user(client, apple, "apple-user-2")
    assert (await client.get("/v1/library", params={"q": "ordering food"}, headers=other)).json()["results"][0]["credit"] == "Ahsan"
    assert (await client.delete("/v1/account", headers=auth)).status_code == 204
    hit = (await client.get("/v1/library", params={"q": "ordering food"}, headers=other)).json()["results"][0]
    assert hit["title"] == "Ordering food" and hit["credit"] is None


async def test_private_scenes_and_reports(client, auth, apple):
    r = (await client.post("/v1/scenarios", json={"title": "Call the plumber", "share": False}, headers=auth)).json()
    assert r["library"]["status"] == "private"
    shared = (await client.post("/v1/scenarios", json={"title": "Buying a train ticket"}, headers=auth)).json()
    tid = shared["library"]["template"]["id"]
    for n in range(3):
        h = await _user(client, apple, f"reporter-{n}")
        assert (await client.post(f"/v1/library/{tid}/report", json={"reason": "wrong"}, headers=h)).json() == {"ok": True}
    assert (await client.get("/v1/library", params={"q": "train ticket"}, headers=auth)).json()["results"] == []
    assert (await client.get("/v1/library", params={"q": "plumber"}, headers=auth)).json()["results"] == []
