from __future__ import annotations

from fastapi import Depends, FastAPI

from app.security.app_attest import attested


def register(app: FastAPI) -> None:
    from app.routers import account, attest, auth

    app.include_router(attest.router)  # attestation endpoints can't require an assertion yet
    guarded = [Depends(attested)]
    for module in (auth, account):
        app.include_router(module.router, dependencies=guarded)
