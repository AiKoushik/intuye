from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app import errors
from app.agents.registry import Graphs
from app.llm.provider import build_llm
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
    app.state.graphs = Graphs(build_llm(settings))
    errors.install(app)
    app.add_middleware(SecurityMiddleware, max_body=settings.max_body_bytes,
                       max_batch_body=settings.max_batch_body_bytes)

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True}

    from app.routers import register

    register(app)
    _mount_dev_extras(app, settings)
    return app


def _mount_dev_extras(app: FastAPI, settings: Settings) -> None:
    """Web test client at /web and optional CORS — development only."""
    if settings.env == "production":
        return
    if settings.cors_origins:
        from fastapi.middleware.cors import CORSMiddleware

        app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
                           allow_methods=["*"], allow_headers=["*"])
    web_dir = Path(settings.web_client_dir) if settings.web_client_dir else Path(__file__).resolve().parents[2] / "web"
    if web_dir.is_dir():
        from fastapi.responses import RedirectResponse
        from fastapi.staticfiles import StaticFiles

        app.mount("/web", StaticFiles(directory=web_dir, html=True), name="web")

        @app.get("/", include_in_schema=False)
        async def root() -> RedirectResponse:
            return RedirectResponse("/web/")


app = create_app()  # for `uvicorn app.main:app`; tests build their own with create_app(settings)
