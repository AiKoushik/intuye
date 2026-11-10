import pytest

from tests.conftest import sign_in

pytestmark = pytest.mark.anyio


async def test_sign_in_refresh_rotation_and_reuse_detection(client, apple):
    s = await sign_in(client, apple)
    me = await client.get("/v1/me", headers={"authorization": f"Bearer {s['access_token']}"})
    assert me.status_code == 200 and me.json()["user"]["display_name"] == "Ahsan"
    assert me.json()["settings"]["dialect"] == "es-419"

    r1 = await client.post("/v1/auth/refresh", json={"refresh_token": s["refresh_token"]})
    assert r1.status_code == 200
    new = r1.json()
    assert new["refresh_token"] != s["refresh_token"]

    # Reusing the rotated token revokes the whole family, including the new token.
    reuse = await client.post("/v1/auth/refresh", json={"refresh_token": s["refresh_token"]})
    assert reuse.status_code == 401 and reuse.json()["error"]["code"] == "refresh_reuse"
    after = await client.post("/v1/auth/refresh", json={"refresh_token": new["refresh_token"]})
    assert after.status_code == 401


async def test_settings_export_and_delete(client, apple, auth):
    r = await client.patch("/v1/me/settings", json={"dialect": "es-MX", "level": 1}, headers=auth)
    assert r.status_code == 200 and r.json()["dialect"] == "es-MX"

    export = await client.get("/v1/account/export", headers=auth)
    assert export.status_code == 200 and export.json()["settings"][0]["dialect"] == "es-MX"

    assert (await client.delete("/v1/account", headers=auth)).status_code == 204
    assert (await client.get("/v1/me", headers=auth)).status_code == 401
