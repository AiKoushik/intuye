"""Builds word batches: gathers candidates from the learner's data, ranks, persists batch + cards."""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.curation import base_lexicon, fsrs, grammar
from app.curation.ranker import Candidate, Pick, select as rank_select
from app.models import (Batch, BatchItem, Card, Lexeme, LexemeEvent, PronunciationAttempt, Scenario, UserSettings,
                        Utterance, utcnow)
from app.services.lexicon import upsert_lexeme

SCENARIO_HORIZON_H = 72
BASE_POOL = 40


async def build_batch(db: AsyncSession, user_id: str, size: int = 7) -> tuple[Batch, list[tuple[Pick, Lexeme]]]:
    now = utcnow()
    settings = await db.get(UserSettings, user_id)
    level = settings.level if settings else 0

    lexemes = list((await db.execute(select(Lexeme).where(Lexeme.user_id == user_id))).scalars())
    cards = {c.lexeme_id: c for c in (await db.execute(select(Card).where(Card.user_id == user_id))).scalars()}
    events = (await db.execute(select(LexemeEvent).where(
        LexemeEvent.user_id == user_id, LexemeEvent.at >= now - timedelta(days=21)))).scalars()
    mentions: dict[str, list] = defaultdict(list)
    for e in events:
        if e.kind in ("said_en", "looked_up"):
            mentions[e.lexeme_id].append(e.at)
    mispron: dict[str, int] = defaultdict(int)
    for a in (await db.execute(select(PronunciationAttempt).where(
            PronunciationAttempt.user_id == user_id, PronunciationAttempt.at >= now - timedelta(days=14),
            PronunciationAttempt.score < 0.7))).scalars():
        mispron[a.lexeme_id] += 1
    scenarios = {s.id: s for s in (await db.execute(select(Scenario).where(
        Scenario.user_id == user_id, Scenario.status == "active"))).scalars()}
    open_items = set((await db.execute(select(BatchItem.lexeme_id).join(Batch).where(
        Batch.user_id == user_id, Batch.completed_at.is_(None)))).scalars())

    utts = list((await db.execute(select(Utterance).where(
        Utterance.user_id == user_id, Utterance.spoken_at >= now - timedelta(days=7)))).scalars())
    topic_counts: dict[str, int] = defaultdict(int)
    for u in utts:
        if u.topic:
            topic_counts[u.topic] += 1
    topic_share = {t: n / max(len(utts), 1) for t, n in topic_counts.items()}

    cands: list[Candidate] = []
    known_es = set()
    for lx in lexemes:
        known_es.add(lx.es)
        card = cards.get(lx.id)
        r = None
        if card and card.reps > 0 and card.last_review_at:
            r = fsrs.retrievability((now - card.last_review_at).total_seconds() / 86400, card.stability)
            if r >= 0.9 and not mispron.get(lx.id):
                continue  # well known; reviews handle it
        sc_title = sc_hours = None
        if lx.topic and lx.topic.startswith("scene:"):
            sc = scenarios.get(lx.topic[6:])
            if sc and sc.starts_at:
                hours = (sc.starts_at - now).total_seconds() / 3600
                if 0 <= hours <= SCENARIO_HORIZON_H:
                    sc_title, sc_hours = sc.title, hours
        cands.append(Candidate(
            key=lx.id, es=lx.es, en=lx.en, origin=lx.origin, topic=None if (lx.topic or "").startswith("scene:") else lx.topic,
            context=lx.context, mentions=mentions.get(lx.id, []), mispronounced_14d=mispron.get(lx.id, 0), retrievability=r,
            scenario_title=sc_title, scenario_hours=sc_hours, base_rank=base_lexicon.rank_of(lx.es),
            due_now=bool(card and card.reps > 0 and card.due_at <= now), in_open_batch=lx.id in open_items))

    added = 0
    for i, (es, en) in enumerate(base_lexicon.BASE):
        if added >= BASE_POOL:
            break
        if es not in known_es:
            cands.append(Candidate(key=f"base:{es}", es=es, en=en, origin="base", base_rank=i + 1))
            added += 1

    seen_triggers = {}
    for u in utts:
        for t in grammar.matches(u.text):
            seen_triggers.setdefault(t.id, (t, u.text))
    for t, example in seen_triggers.values():
        if t.es not in known_es:
            cands.append(Candidate(key=f"grammar:{t.id}", es=t.es, en=t.en, origin="grammar", context=example,
                                   grammar_lesson=f"You've said “{example[:40]}” — {t.lesson.lower()}"))

    picks = rank_select(cands, now, level, topic_share, size)

    batch = Batch(user_id=user_id)
    db.add(batch)
    await db.flush()
    out: list[tuple[Pick, Lexeme]] = []
    for pos, p in enumerate(picks):
        c = p.candidate
        lx = next((x for x in lexemes if x.id == c.key), None)
        if lx is None:
            lx = await upsert_lexeme(db, user_id, c.es, c.en, origin=c.origin, context=c.context)
        if lx.id not in cards:
            card = Card(lexeme_id=lx.id, user_id=user_id, state="new", due_at=now)
            db.add(card)
            cards[lx.id] = card
        else:
            cards[lx.id].due_at = min(cards[lx.id].due_at, now)  # struggling items come back now
        db.add(BatchItem(batch_id=batch.id, lexeme_id=lx.id, position=pos, reason=p.reason[:200],
                         reason_kind=p.reason_kind, score=p.score))
        out.append((p, lx))
    await db.commit()
    return batch, out


def to_state(card: Card) -> fsrs.CardState:
    return fsrs.CardState(state=card.state, stability=card.stability, difficulty=card.difficulty, reps=card.reps,
                          lapses=card.lapses, last_review_at=card.last_review_at, due_at=card.due_at)
