"""Serving the pack's 60-second grammar lessons. The lessons themselves are language content in the pack."""
from __future__ import annotations

import random

from app.languages import LanguagePack


def lesson_id_for(target: str, pack: LanguagePack) -> str | None:
    """The lesson behind a grammar item in a batch (its text is the trigger's target pattern)."""
    return next((t.id for t in pack.grammar if t.target == target and t.id in pack.lessons), None)


def lesson(lesson_id: str, pack: LanguagePack) -> dict | None:
    data = pack.lessons.get(lesson_id)
    if data is None:
        return None
    trig = next((t for t in pack.grammar if t.id == lesson_id), None)
    # The right answer is written first; shuffle so it isn't always the top option.
    options = list(data.check_options)
    right = options[data.check_answer]
    random.shuffle(options)
    return {"id": lesson_id, "title": data.title, "pattern": data.pattern, "rule": data.rule,
            "examples": [{"en": en, "target": t} for en, t in data.examples],
            "check": {"prompt": data.check_prompt, "options": options, "answer": options.index(right)},
            "target": trig.target if trig else data.pattern, "en": trig.en if trig else ""}
