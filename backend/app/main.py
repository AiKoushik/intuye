from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import errors
from app.config import Settings, get_settings
from app.db import Database
from app.security.middleware import SecurityMiddleware
from app.security.apple import AppleIdentityVerifier
from app.security.app_attest import AppAttestService
from app.security.ratelimit import RateLimiter
from app.security.tokens import TokenService


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    db = Database(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.env != "production":
            await db.create_all()  # production uses migrations
        yield
        await db.dispose()

    app = FastAPI(title="LangCoach API", version="0.1.0", lifespan=lifespan,
                  docs_url=None if settings.env == "production" else "/docs")
    app.state.settings = settings
    app.state.db = db
    app.state.ratelimiter = RateLimiter()
    app.state.tokens = TokenService(settings)
    app.state.apple = AppleIdentityVerifier(settings)
    app.state.attest = AppAttestService(settings)
    errors.install(app)
    app.add_middleware(SecurityMiddleware, max_body=settings.max_body_bytes,
                       max_batch_body=settings.max_batch_body_bytes)

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True}

    from app.routers import register

    register(app)
    return app


app = create_app()  # for `uvicorn app.main:app`; tests build their own with create_app(settings)
