"""FSRS-4.5 scheduler (Ye, Su & Cao, KDD Aug 2022; FSRS-4.5 formulas and default weights from the
open-spaced-repetition project, 2023). Pure functions; the caller persists the result."""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

W = [0.4872, 1.4003, 3.7145, 13.8206, 5.1618, 1.2298, 0.8975, 0.031, 1.6474, 0.1367, 1.0461,
     2.1072, 0.0793, 0.3246, 1.587, 0.2272, 2.8755]
DECAY = -0.5
FACTOR = 19 / 81
DESIRED_RETENTION = 0.9
RELEARN_MINUTES = 10
MAX_INTERVAL_DAYS = 365

AGAIN, HARD, GOOD, EASY = 1, 2, 3, 4


@dataclass(frozen=True)
class CardState:
    state: str = "new"  # new | learning | review | relearning
    stability: float = 0.0
    difficulty: float = 0.0
    reps: int = 0
    lapses: int = 0
    last_review_at: datetime | None = None
    due_at: datetime | None = None


@dataclass(frozen=True)
class Scheduled:
    card: CardState
    scheduled_days: float
    elapsed_days: float
    retrievability: float | None


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def retrievability(elapsed_days: float, stability: float) -> float:
    if stability <= 0:
        return 0.0
    return (1 + FACTOR * max(elapsed_days, 0) / stability) ** DECAY


def interval_days(stability: float, retention: float = DESIRED_RETENTION) -> float:
    days = stability / FACTOR * (retention ** (1 / DECAY) - 1)
    return _clamp(round(days), 1, MAX_INTERVAL_DAYS)


def init_stability(g: int) -> float:
    return max(W[g - 1], 0.1)


def init_difficulty(g: int) -> float:
    return _clamp(W[4] - (g - 3) * W[5], 1, 10)


def next_difficulty(d: float, g: int) -> float:
    d2 = d - W[6] * (g - 3)
    return _clamp(W[7] * init_difficulty(4) + (1 - W[7]) * d2, 1, 10)


def stability_after_success(d: float, s: float, r: float, g: int) -> float:
    hard = W[15] if g == HARD else 1.0
    easy = W[16] if g == EASY else 1.0
    return s * (1 + math.exp(W[8]) * (11 - d) * s ** (-W[9]) * (math.exp(W[10] * (1 - r)) - 1) * hard * easy)


def stability_after_lapse(d: float, s: float, r: float) -> float:
    return min(W[11] * d ** (-W[12]) * ((s + 1) ** W[13] - 1) * math.exp(W[14] * (1 - r)), s)


def schedule(card: CardState, rating: int, now: datetime) -> Scheduled:
    if rating not in (AGAIN, HARD, GOOD, EASY):
        raise ValueError("rating must be 1-4")
    elapsed = (now - card.last_review_at).total_seconds() / 86400 if card.last_review_at else 0.0

    if card.state == "new":
        s, d = init_stability(rating), init_difficulty(rating)
        r = None
        if rating == AGAIN:
            new = replace(card, state="learning", stability=s, difficulty=d, reps=card.reps + 1,
                          last_review_at=now, due_at=now + timedelta(minutes=RELEARN_MINUTES))
            return Scheduled(new, RELEARN_MINUTES / 1440, elapsed, r)
        days = interval_days(s)
        new = replace(card, state="review", stability=s, difficulty=d, reps=card.reps + 1, last_review_at=now,
                      due_at=now + timedelta(days=days))
        return Scheduled(new, days, elapsed, r)

    r = retrievability(elapsed, card.stability)
    d = next_difficulty(card.difficulty, rating)
    if rating == AGAIN:
        s = stability_after_lapse(card.difficulty, card.stability, r)
        new = replace(card, state="relearning", stability=max(s, 0.1), difficulty=d, reps=card.reps + 1,
                      lapses=card.lapses + 1, last_review_at=now, due_at=now + timedelta(minutes=RELEARN_MINUTES))
        return Scheduled(new, RELEARN_MINUTES / 1440, elapsed, r)

    if card.state in ("learning", "relearning"):
        s = card.stability  # short-term step: graduate without changing long-term memory estimate
    else:
        s = stability_after_success(card.difficulty, card.stability, r, rating)
    days = interval_days(s)
    new = replace(card, state="review", stability=s, difficulty=d, reps=card.reps + 1, last_review_at=now,
                  due_at=now + timedelta(days=days))
    return Scheduled(new, days, elapsed, r)
