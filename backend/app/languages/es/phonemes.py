"""Spanish grapheme-to-phoneme rules for pronunciation feedback (the comparison itself is language-neutral).

Spanish spelling is close to phonemic, so a rule-based G2P is accurate enough to compare what the
learner was asked to say with what on-device recognition heard, phoneme by phoneme. It stands in for
acoustic goodness-of-pronunciation scoring until an audio model runs on the device.
"""
from __future__ import annotations

import unicodedata

VOWELS = set("aeiou")
# What a learner should hear about a sound they missed.
TIPS = {
    "r": "Roll the rr: tap the tip of your tongue several times.",
    "ɾ": "A single r is one quick tap, like the tt in American 'butter'.",
    "x": "The j and the g before e or i come from the back of the throat, like a soft 'h'.",
    "ɲ": "ñ is like the 'ny' in 'canyon'.",
    "θ": "In Spain, c before e or i and z sound like English 'th' in 'think'.",
    "ʝ": "ll and y sound like the y in 'yes'.",
    "tʃ": "ch is like English 'ch' in 'church'.",
    "e": "Spanish e is short and pure, as in 'met', without gliding into 'ay'.",
    "o": "Spanish o is short and pure, without gliding into 'ow'.",
    "u": "Spanish u is like 'oo' in 'food'; it's silent in que, qui, gue and gui.",
}


def _strip_accents(word: str) -> str:
    out = []
    for ch in word:
        if ch in "ñÑüÜ":
            out.append(ch.lower())
            continue
        out.append("".join(c for c in unicodedata.normalize("NFD", ch) if unicodedata.category(c) != "Mn"))
    return "".join(out).lower()


def word_phonemes(word: str, dialect: str = "es-419") -> list[str]:
    w = _strip_accents(word)
    spain = dialect == "es-ES"
    out: list[str] = []
    i = 0
    while i < len(w):
        c, nxt = w[i], w[i + 1] if i + 1 < len(w) else ""
        two = w[i:i + 2]
        if two == "ch":
            out.append("tʃ"); i += 2; continue
        if two == "ll":
            out.append("ʝ"); i += 2; continue
        if two == "rr":
            out.append("r"); i += 2; continue
        if two == "qu":
            out.append("k"); i += 2; continue
        if two == "gu" and w[i + 2:i + 3] in ("e", "i"):
            out.append("g"); i += 2; continue
        if two == "gü":
            out += ["g", "w"]; i += 2; continue
        if c == "h":
            i += 1; continue
        if c == "c":
            out.append(("θ" if spain else "s") if nxt in ("e", "i") else "k"); i += 1; continue
        if c == "z":
            out.append("θ" if spain else "s"); i += 1; continue
        if c == "g":
            out.append("x" if nxt in ("e", "i") else "g"); i += 1; continue
        if c == "j":
            out.append("x"); i += 1; continue
        if c in ("v", "b"):
            out.append("b"); i += 1; continue
        if c == "ñ":
            out.append("ɲ"); i += 1; continue
        if c == "y":
            out.append("i" if (i == len(w) - 1 or nxt not in VOWELS) else "ʝ"); i += 1; continue
        if c == "x":
            out += ["k", "s"]; i += 1; continue
        if c == "r":
            prev = w[i - 1] if i else ""
            out.append("r" if i == 0 or prev in ("n", "l", "s") else "ɾ"); i += 1; continue
        if c == "ü":
            out.append("w"); i += 1; continue
        out.append(c); i += 1
    return out
