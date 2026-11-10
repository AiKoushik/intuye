import pytest

pytestmark = pytest.mark.anyio


async def test_health_has_security_headers(client):
    r = await client.get("/health")
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "x-request-id" in r.headers
