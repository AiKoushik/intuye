"""Word-level pronunciation proxy until a phoneme model (GOP over wav2vec 2.0) lands in P2.

Compares what on-device recognition heard with what was expected, after mapping Spanish spellings that
sound the same (b/v, silent h, ll/y, and c/z/s for seseo dialects) so spelling isn't penalised.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.curation.text import fold


def phonetic(text: str, dialect: str = "es-419") -> str:
    t = fold(text)
    t = re.sub(r"[^a-z ]", "", t)
    t = t.replace("ll", "y").replace("v", "b").replace("qu", "k").replace("ch", "X")
    t = re.sub(r"h", "", t)
    t = re.sub(r"c(?=[ei])", "s" if dialect != "es-ES" else "z", t)
    t = t.replace("c", "k")
    if dialect != "es-ES":
        t = t.replace("z", "s")
    t = re.sub(r"g(?=[ei])", "j", t)
    return re.sub(r"\s+", " ", t).strip()


def score(expected: str, heard: str, dialect: str = "es-419") -> float:
    a, b = phonetic(expected, dialect), phonetic(heard, dialect)
    if not a or not b:
        return 0.0
    return round(SequenceMatcher(None, a, b).ratio(), 3)
