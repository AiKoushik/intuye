"""Rough level estimate and the weekly reflection. Plain arithmetic over what the learner did."""
from __future__ import annotations

BANDS = ["Pre-A1", "A1", "A2", "B1", "B2", "C1"]
# Words kept (retrievability >= 0.9) needed for each level, after typical CEFR vocabulary sizes.
VOCAB_STEPS = [0, 50, 150, 400, 900, 1800]


def estimate(kept: int, spanish_share: float | None, avg_spanish_words: float | None) -> dict:
    """70% vocabulary, 30% how much of your Spanish is actually Spanish and how long your sentences run."""
    vocab_level = max(i for i, n in enumerate(VOCAB_STEPS) if kept >= n)
    fluency_level = vocab_level
    if spanish_share is not None and avg_spanish_words is not None:
        fluency_level = min(5, int(spanish_share * 3 + min(avg_spanish_words, 12) / 6))
    level = round(0.7 * vocab_level + 0.3 * fluency_level)
    return {"level": level, "band": BANDS[level], "basis": {"words_kept": kept, "spanish_share": spanish_share,
                                                            "avg_spanish_words": avg_spanish_words}}


def reflection_line(sentences: int, spanish_share_now: float | None, spanish_share_before: float | None,
                    kept_new: int, rehearsed: int) -> str:
    """One calm, specific sentence. Never guilt."""
    if sentences == 0 and rehearsed == 0 and kept_new == 0:
        return "A quiet week. Whenever you're ready, say one thing on the Say tab."
    parts = []
    if spanish_share_now is not None and spanish_share_before is not None and spanish_share_now > spanish_share_before + 0.03:
        parts.append(f"more of your sentences were Spanish than the week before ({round(spanish_share_now * 100)}%)")
    if rehearsed:
        parts.append(f"you rehearsed {rehearsed} {'scene' if rehearsed == 1 else 'scenes'}")
    if kept_new:
        parts.append(f"{kept_new} {'word' if kept_new == 1 else 'words'} stuck")
    if not parts:
        parts.append(f"you said {sentences} {'thing' if sentences == 1 else 'things'} worth learning from")
    text = ", ".join(parts[:-1]) + (" and " if len(parts) > 1 else "") + parts[-1]
    return text[0].upper() + text[1:] + "."
