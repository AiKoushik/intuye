from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def settings() -> Settings:
    return Settings(env="test", database_url="sqlite+aiosqlite:///:memory:", app_attest_mode="off",
                    llm_provider="fake")


@pytest.fixture
async def app(settings: Settings):
    application = create_app(settings)
    await application.state.db.create_all()
    yield application
    await application.state.db.dispose()


@pytest.fixture
async def client(app) -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
