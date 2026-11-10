"""Deterministic batch ranker. See docs/09-curation-engine.md. Pure: no I/O."""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Candidate:
    key: str  # lexeme id, or "base:<es>" / "grammar:<id>" for items not stored yet
    es: str
    en: str
    origin: str  # spoken | base | scenario | grammar
    topic: str | None = None
    context: str | None = None
    mentions: list[datetime] = field(default_factory=list)  # said_en / looked_up events
    mispronounced_14d: int = 0
    retrievability: float | None = None  # None = never reviewed
    scenario_title: str | None = None
    scenario_hours: float | None = None
    base_rank: int | None = None
    grammar_lesson: str | None = None
    due_now: bool = False
    in_open_batch: bool = False


@dataclass
class Pick:
    candidate: Candidate
    score: float
    reason_kind: str
    reason: str


def base_weight(level: int) -> float:
    return {0: 2.5, 1: 2.0, 2: 1.5, 3: 1.1, 4: 0.8}.get(level, 0.6)


def _recency_frequency(mentions: list[datetime], now: datetime) -> float:
    raw = sum(math.exp(-max((now - m).total_seconds(), 0) / 86400 / 7) for m in mentions)
    return min(math.log1p(raw) / math.log1p(5), 1.0)


def score(c: Candidate, now: datetime, level: int, topic_share: dict[str, float]) -> tuple[float, str, str]:
    parts: dict[str, float] = {}
    if c.scenario_hours is not None and c.scenario_hours >= 0:
        parts["scenario"] = 3.0 / (1 + c.scenario_hours / 24)
    if c.mentions:
        parts["spoken"] = 1.2 + 1.8 * _recency_frequency(c.mentions, now)  # your words always outrank the base list
    struggle = 0.0
    if c.retrievability is not None:
        struggle += 1 - c.retrievability
    struggle = min(struggle + 0.5 * c.mispronounced_14d, 1.0)
    if struggle:
        parts["struggle"] = 2.0 * struggle
    if c.topic and topic_share.get(c.topic):
        parts["topic"] = 1.0 * topic_share[c.topic]
    if c.base_rank:
        parts["base"] = 0.4 * base_weight(level) / c.base_rank ** 0.3  # max 1.0: fills gaps, never leads
    if c.grammar_lesson:
        parts["grammar"] = 1.6
    total = sum(parts.values()) - (5.0 if (c.due_now or c.in_open_batch) else 0.0)
    kind = max(parts, key=parts.get) if parts else "base"
    return total, kind, reason_text(kind, c, now)


def reason_text(kind: str, c: Candidate, now: datetime) -> str:
    if kind == "scenario" and c.scenario_title:
        when = "today" if (c.scenario_hours or 0) < 18 else ("tomorrow" if (c.scenario_hours or 0) < 42 else "soon")
        return f"For {c.scenario_title.lower()} {when}"
    if kind == "spoken":
        week = [m for m in c.mentions if (now - m).days < 7]
        n = len(week) or len(c.mentions)
        return f"You said “{c.en}” {n} time{'s' if n != 1 else ''} this week" if week else f"You said “{c.en}” recently"
    if kind == "struggle":
        if c.mispronounced_14d:
            return f"You've mispronounced this {c.mispronounced_14d}× lately"
        return "Slipping — worth a refresh"
    if kind == "topic" and c.topic:
        return f"You've been talking about {c.topic}"
    if kind == "grammar" and c.grammar_lesson:
        return c.grammar_lesson
    if c.base_rank and c.base_rank <= 10:
        return "A phrase that gets you unstuck"
    return f"One of the {500 if (c.base_rank or 999) <= 500 else 1000} most common words"


def select(cands: list[Candidate], now: datetime, level: int, topic_share: dict[str, float], size: int = 7) -> list[Pick]:
    size = max(5, min(size, 10))
    scored = []
    for c in cands:
        s, kind, why = score(c, now, level, topic_share)
        if s > 0:
            scored.append(Pick(c, round(s, 4), kind, why))
    scored.sort(key=lambda p: (-p.score, p.candidate.es))

    picks: list[Pick] = []
    per_topic: Counter[str] = Counter()
    grammar = 0
    seen: set[str] = set()
    for p in scored:
        c = p.candidate
        if c.es in seen:
            continue
        if c.topic and per_topic[c.topic] >= 3:
            continue
        if p.reason_kind == "grammar" and grammar >= 2:
            continue
        picks.append(p)
        seen.add(c.es)
        per_topic[c.topic or ""] += 1 if c.topic else 0
        grammar += p.reason_kind == "grammar"
        if len(picks) == size:
            break

    if level <= 2 and picks and not any(p.candidate.base_rank for p in picks):
        base = next((p for p in scored if p.candidate.base_rank and p.candidate.es not in seen), None)
        if base:
            picks[-1] = base
    return picks
