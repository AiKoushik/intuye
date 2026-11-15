"""Language registry. Everything specific to a target language lives in its pack; this maps codes to packs.

Which packs are offered is configuration (`LANGUAGES` in settings), not code.
"""
from __future__ import annotations

from app.languages import native_en
from app.languages.base import LanguagePack, Lesson, Trigger, Variety
from app.languages.es import PACK as SPANISH

ALL: dict[str, LanguagePack] = {p.code: p for p in (SPANISH,)}
DEFAULT = "es"

__all__ = ["ALL", "DEFAULT", "LanguagePack", "Lesson", "Trigger", "Variety", "native_en", "default_variety", "enabled", "for_variety", "get", "variety_codes"]


def enabled(codes: str | None = None) -> list[LanguagePack]:
    """Packs switched on by config, e.g. LANGUAGES="es,fr". Unknown codes are ignored."""
    wanted = [c.strip() for c in (codes or DEFAULT).split(",") if c.strip()]
    return [ALL[c] for c in wanted if c in ALL] or [ALL[DEFAULT]]


def get(code: str | None) -> LanguagePack:
    return ALL.get(code or DEFAULT, ALL[DEFAULT])


def for_variety(variety: str | None) -> LanguagePack:
    """The pack a learner is on, from their variety setting ("es-419" -> Spanish)."""
    return get((variety or DEFAULT).split("-")[0].lower())


def variety_codes(codes: str | None = None) -> set[str]:
    return {v.code for p in enabled(codes) for v in p.varieties}


def default_variety() -> str:
    return ALL[DEFAULT].default_variety
