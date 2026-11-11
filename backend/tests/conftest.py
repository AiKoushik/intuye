from __future__ import annotations

import secrets

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app
from app.security.apple import AppleIdentityVerifier
from tests.fakes import FakeAppleID


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def settings() -> Settings:
    # Isolated from backend/.env and local overrides, so a developer's settings never change test results.
    return Settings(_env_file=None, env="test", database_url="sqlite+aiosqlite:///:memory:", app_attest_mode="off",
                    llm_provider="fake", dev_login_enabled=False, web_client_dir="", cors_origins="")


@pytest.fixture
def apple(settings: Settings) -> FakeAppleID:
    return FakeAppleID(settings.apple_bundle_id)


@pytest.fixture
async def app(settings: Settings, apple: FakeAppleID):
    application = create_app(settings)
    application.state.apple = AppleIdentityVerifier(settings, jwks_provider=apple.jwks)
    await application.state.db.create_all()
    yield application
    await application.state.db.dispose()


@pytest.fixture
async def client(app) -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def sign_in(client: AsyncClient, apple: FakeAppleID, sub: str = "apple-user-1", headers: dict | None = None) -> dict:
    nonce = secrets.token_hex(16)
    r = await client.post("/v1/auth/apple", json={"identity_token": apple.identity_token(sub, nonce), "raw_nonce": nonce,
                                                  "display_name": "Ahsan"}, headers=headers or {})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
async def auth(client, apple) -> dict:
    """Bearer headers for a signed-in user."""
    session = await sign_in(client, apple)
    return {"authorization": f"Bearer {session['access_token']}"}
