"""Cheap, deterministic text helpers: tokenising, telling target-language words from English, normalising entries.

Language-neutral: everything specific to a language comes from its pack.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

from app.languages import LanguagePack, native_en


@lru_cache(maxsize=16)
def _token_re(letters: str) -> re.Pattern[str]:
    return re.compile(rf"[{letters}']+")


def tokens(text: str, pack: LanguagePack) -> list[str]:
    return [t.lower() for t in _token_re(pack.letters).findall(text)]


def is_target_token(tok: str, pack: LanguagePack) -> bool | None:
    """True when the token is clearly the target language, False when clearly English, None when unsure."""
    t = tok.lower()
    if any(c in pack.marks for c in t):
        return True
    in_t, in_en = t in pack.hint_words, t in native_en.HINT_WORDS
    if in_t and not in_en:
        return True
    if in_en and not in_t:
        return False
    if t.endswith(pack.suffixes):
        return True
    if t.endswith(native_en.SUFFIXES):
        return False
    return None


def english_share(text: str, pack: LanguagePack) -> float:
    """Share of classifiable tokens that look English (0 = all target language, 1 = all English)."""
    votes = [is_target_token(t, pack) for t in tokens(text, pack)]
    known = [v for v in votes if v is not None]
    if not known:
        return 1.0
    return round(sum(1 for v in known if v is False) / len(known), 3)


def looks_target(text: str, pack: LanguagePack) -> bool:
    if any(c in pack.marks for c in text):
        return True
    return english_share(text, pack) < 0.35


def normalize_entry(phrase: str, pack: LanguagePack) -> str:
    """A phrase as a dictionary entry: lower case, outer punctuation and a leading article removed."""
    p = phrase.strip().lower()
    p = re.sub(r"^[¿¡\"'(«]+|[?!.,;:\"')»]+$", "", p)
    if pack.articles:
        p = re.sub(rf"^(?:{'|'.join(map(re.escape, pack.articles))})\s+", "", p)
    return re.sub(r"\s+", " ", p)[:120]


def fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")
