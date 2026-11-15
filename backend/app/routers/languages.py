"""Which target languages and varieties this server offers. Clients build pickers, speech and copy from this."""
from __future__ import annotations

from fastapi import APIRouter, Request

from app import languages

router = APIRouter(prefix="/v1/languages", tags=["languages"])


@router.get("")
async def offered(request: Request) -> dict:
    packs = languages.enabled(request.app.state.settings.languages)
    return {"default": packs[0].code, "languages": [p.public() for p in packs]}
