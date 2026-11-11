import json
import secrets

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app
from app.security.apple import AppleIdentityVerifier
from tests.fakes import FakeAppleID, FakeAttestDevice

pytestmark = pytest.mark.anyio


async def test_attest_register_then_signed_requests():
    base = Settings(_env_file=None, env="test", database_url="sqlite+aiosqlite:///:memory:", llm_provider="fake",
                    dev_login_enabled=False)
    device = FakeAttestDevice(base.app_id)
    settings = base.model_copy(update={"app_attest_mode": "enforce", "app_attest_root_pem": device.root_pem})
    app = create_app(settings)
    apple = FakeAppleID(settings.apple_bundle_id)
    app.state.apple = AppleIdentityVerifier(settings, jwks_provider=apple.jwks)
    await app.state.db.create_all()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        challenge = (await c.get("/v1/attest/challenge")).json()["challenge"]
        reg = await c.post("/v1/attest/register", json={"key_id": device.key_id_b64,
                                                        "attestation": device.attest(challenge), "challenge": challenge})
        assert reg.status_code == 200, reg.text

        # Unsigned request is rejected.
        assert (await c.post("/v1/auth/refresh", json={"refresh_token": "x" * 30})).status_code == 401

        nonce = secrets.token_hex(16)
        body = json.dumps({"identity_token": apple.identity_token("sub-1", nonce), "raw_nonce": nonce}).encode()
        r = await c.post("/v1/auth/apple", content=body,
                         headers={"content-type": "application/json", **device.headers("POST", "/v1/auth/apple", body)})
        assert r.status_code == 200, r.text
        bearer = {"authorization": f"Bearer {r.json()['access_token']}"}

        me = await c.get("/v1/me", headers={**bearer, **device.headers("GET", "/v1/me")})
        assert me.status_code == 200

        # A tampered path (signature over a different request) fails.
        bad = await c.get("/v1/me", headers={**bearer, **device.headers("GET", "/v1/account/export")})
        assert bad.status_code == 401 and bad.json()["error"]["code"] == "attestation_failed"
    await app.state.db.dispose()
