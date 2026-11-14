from __future__ import annotations

from fastapi import Depends, FastAPI

from app.security.app_attest import attested


def register(app: FastAPI) -> None:
    from app.routers import account, attest, auth, coach, lessons, library, practice, progress, rehearsals, scenarios, utterances, words

    app.include_router(attest.router)  # attestation endpoints can't require an assertion yet
    guarded = [Depends(attested)]
    for module in (auth, account, coach, utterances, words, scenarios, library, practice, lessons, rehearsals, progress):
        app.include_router(module.router, dependencies=guarded)

    s = app.state.settings
    if s.dev_login_enabled and s.env != "production":
        from app.routers import dev

        app.include_router(dev.router, dependencies=guarded)
