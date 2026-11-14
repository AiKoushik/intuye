"""Spanish grapheme-to-phoneme rules and phoneme-level comparison for pronunciation feedback.

Spanish spelling is close to phonemic, so a rule-based G2P is accurate enough to compare what the
learner was asked to say with what on-device recognition heard, phoneme by phoneme. It stands in for
acoustic goodness-of-pronunciation scoring until an audio model runs on the device.
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

VOWELS = set("aeiou")
WORD = re.compile(r"[a-záéíóúüñ]+", re.I)

# What a learner should hear about a mismatch, keyed by (expected, heard) or expected alone.
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


def g2p(text: str, dialect: str = "es-419") -> list[tuple[str, list[str]]]:
    return [(m.group(0), word_phonemes(m.group(0), dialect)) for m in WORD.finditer(text)]


def compare(expected: str, heard: str, dialect: str = "es-419") -> dict:
    """Word-by-word, phoneme-by-phoneme comparison. Words the recogniser didn't return count as missed."""
    exp, got = g2p(expected, dialect), g2p(heard, dialect)
    exp_keys = ["".join(p) for _, p in exp]
    got_keys = ["".join(p) for _, p in got]
    pairs: dict[int, int] = {}
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, exp_keys, got_keys, autojunk=False).get_opcodes():
        if tag in ("equal", "replace"):
            for k in range(min(i2 - i1, j2 - j1)):
                pairs[i1 + k] = j1 + k
    words, total, matched, tips = [], 0, 0, []
    for i, (word, phons) in enumerate(exp):
        heard_phons = got[pairs[i]][1] if i in pairs else []
        marks = [{"p": p, "ok": False} for p in phons]
        for tag, a1, a2, b1, b2 in SequenceMatcher(None, phons, heard_phons, autojunk=False).get_opcodes():
            if tag == "equal":
                for k in range(a1, a2):
                    marks[k]["ok"] = True
            elif tag == "replace":
                for k in range(a1, a2):
                    off = k - a1
                    marks[k]["heard"] = heard_phons[b1 + off] if b1 + off < b2 else ""
        ok_count = sum(m["ok"] for m in marks)
        total += len(marks); matched += ok_count
        for m in marks if i in pairs else []:  # a word that wasn't heard at all needs "say it", not a sound tip
            if not m["ok"] and m["p"] in TIPS and TIPS[m["p"]] not in tips:
                tips.append(TIPS[m["p"]])
        words.append({"word": word, "heard": got[pairs[i]][0] if i in pairs else None, "ok": bool(marks) and ok_count == len(marks),
                      "phonemes": marks})
    score = round(matched / total, 3) if total else 0.0
    return {"score": score, "ok": score >= 0.85, "words": words, "tips": tips[:2]}
