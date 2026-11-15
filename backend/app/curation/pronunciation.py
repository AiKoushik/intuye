"""Phoneme-level comparison of what the learner was asked to say with what recognition heard.

Language-neutral: the pack turns spelling into phonemes and supplies a tip per sound. This stands in
for acoustic goodness-of-pronunciation scoring until an audio model runs on the device.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.languages import LanguagePack, for_variety


def g2p(text: str, pack: LanguagePack, variety: str) -> list[tuple[str, list[str]]]:
    return [(m.group(0), pack.phonemes(m.group(0), variety)) for m in re.finditer(rf"[{pack.letters}]+", text)]


def compare(expected: str, heard: str, variety: str) -> dict:
    """Word-by-word, phoneme-by-phoneme comparison. Words the recogniser didn't return count as missed."""
    pack = for_variety(variety)
    exp, got = g2p(expected, pack, variety), g2p(heard, pack, variety)
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
            tip = pack.sound_tips.get(m["p"])
            if not m["ok"] and tip and tip not in tips:
                tips.append(tip)
        words.append({"word": word, "heard": got[pairs[i]][0] if i in pairs else None, "ok": bool(marks) and ok_count == len(marks),
                      "phonemes": marks})
    score = round(matched / total, 3) if total else 0.0
    return {"score": score, "ok": score >= 0.85, "words": words, "tips": tips[:2]}
