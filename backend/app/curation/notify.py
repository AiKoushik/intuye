"""Notification planner: what to send in the next few days, inside the learner's budget.

Rules (T5): at most `budget` a day, none in quiet hours, never two within an hour, and every
notification says why it's there. Candidates are ranked; lower-priority ones are dropped first.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

MIN_GAP = timedelta(hours=1)
EVENING = time(19, 0)
REVIEW_AT = time(18, 0)
REFLECT_AT = time(9, 30)


@dataclass
class Candidate:
    id: str
    kind: str  # scene_soon | scene_eve | review | reflection
    fire_at: datetime  # aware
    title: str
    body: str
    why: str
    priority: int  # lower sends first
    scenario_id: str | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class SceneIn:
    id: str
    title: str
    starts_at: datetime
    phrases: int
    rescue: int


def _hm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def in_quiet(local: datetime, start: time, end: time) -> bool:
    t = local.time()
    return (t >= start or t < end) if start > end else (start <= t < end)


def plan(now: datetime, tz: str, budget: int, quiet_start: str, quiet_end: str, scenes: list[SceneIn],
         due_by: callable, days: int = 7, language: str = "Spanish") -> tuple[list[Candidate], list[dict]]:
    """Returns (scheduled, suppressed). `due_by(dt)` counts review cards due by that moment."""
    zone = ZoneInfo(tz)
    qs, qe = _hm(quiet_start), _hm(quiet_end)
    local_now = now.astimezone(zone)
    horizon = now + timedelta(days=days)
    cands: list[Candidate] = []

    for s in scenes:
        if not (now < s.starts_at <= horizon + timedelta(days=1)):
            continue
        start_local = s.starts_at.astimezone(zone)
        soon = s.starts_at - timedelta(hours=2)
        cands.append(Candidate(f"scene-soon-{s.id}", "scene_soon", soon, f"{s.title} in 2 hours",
                               f"Run the rescue drill: {s.rescue} phrases for when you get stuck.",
                               f"You have {s.title.lower()} at {start_local:%H:%M}.", 0, s.id))
        eve_day = (start_local - timedelta(days=1)).date()
        eve = datetime.combine(eve_day, EVENING, zone)
        cands.append(Candidate(f"scene-eve-{s.id}", "scene_eve", eve, f"{s.title} tomorrow",
                               f"{s.phrases} phrases ready. Ten minutes tonight makes tomorrow easier.",
                               f"It's on {start_local:%A} at {start_local:%H:%M}.", 1, s.id))

    for d in range(days + 1):
        day = (local_now + timedelta(days=d)).date()
        at = datetime.combine(day, REVIEW_AT, zone)
        n = due_by(at)
        if n >= 3:
            cands.append(Candidate(f"review-{day.isoformat()}", "review", at, f"{n} words ready",
                                   f"About {max(2, round(n * 0.25))} minutes. They're from things you said.",
                                   "Reviewing right before you'd forget is what makes words stick.", 2, extra={"count": n}))
        if day.weekday() == 0:
            cands.append(Candidate(f"reflection-{day.isoformat()}", "reflection", datetime.combine(day, REFLECT_AT, zone),
                                   f"Your week in {language}", "One card: what stuck, what you said, what's next.",
                                   "A Monday look back. No streaks, no guilt.", 3))

    scheduled: list[Candidate] = []
    suppressed: list[dict] = []
    per_day: dict = {}
    for c in sorted(cands, key=lambda c: (c.priority, c.fire_at)):
        local = c.fire_at.astimezone(zone)
        if c.fire_at <= now or c.fire_at > horizon:
            continue
        if in_quiet(local, qs, qe):
            # Scene reminders move to just before quiet hours start; others are dropped.
            if c.kind.startswith("scene"):
                # Scene reminders move to half an hour before that night's quiet hours begin; others are dropped.
                evening = local.date() - timedelta(days=1) if (qs > qe and local.time() < qe) else local.date()
                moved = datetime.combine(evening, qs, zone) - timedelta(minutes=30)
                if now < moved < c.fire_at and not in_quiet(moved, qs, qe):
                    c.fire_at, local = moved, moved
                else:
                    suppressed.append({"id": c.id, "kind": c.kind, "reason": "quiet hours"}); continue
            else:
                suppressed.append({"id": c.id, "kind": c.kind, "reason": "quiet hours"}); continue
        day = local.date()
        if per_day.get(day, 0) >= budget:
            suppressed.append({"id": c.id, "kind": c.kind, "reason": "daily limit"}); continue
        if any(abs(c.fire_at - o.fire_at) < MIN_GAP for o in scheduled):
            suppressed.append({"id": c.id, "kind": c.kind, "reason": "too close to another"}); continue
        per_day[day] = per_day.get(day, 0) + 1
        scheduled.append(c)
    scheduled.sort(key=lambda c: c.fire_at)
    return scheduled, suppressed
