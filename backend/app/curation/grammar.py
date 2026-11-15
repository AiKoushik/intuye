"""Grammar on demand: which of the pack's triggers the learner's own sentence hits."""
from __future__ import annotations

from app.languages import LanguagePack, Trigger


def matches(text: str, pack: LanguagePack) -> list[Trigger]:
    return [t for t in pack.grammar if t.pattern.search(text)]
