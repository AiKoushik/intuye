# Curation engine

The curation engine answers one question several times a day: **which 5–10 Spanish items should this
person meet next, and why?** It is deterministic Python over the learner's own data, so every pick is
explainable and testable. LLMs are used upstream (to turn speech into Spanish lexemes) and
downstream (prep packs), never to choose.

## Candidates

| Pool | Source | Example |
|---|---|---|
| **Spoken** | English words you said that map to Spanish lexemes you haven't learned | *mind → mente* |
| **Struggling** | Learned items with low retrievability, recent "Forgot", or mispronunciation | *muela* |
| **Scenario** | Key phrases of scenarios starting within 72 h | *me duele* |
| **Base** | High-frequency core not yet known, in rank order | *tiempo*, *poder* |
| **Grammar** | Lexemes attached to a grammar trigger seen in your sentences | *que + subjunctive* |

## Score

For each candidate *i*:

```
score_i = 3.0 · scenario_urgency_i      # 1 / (1 + hours_until_scenario / 24), 0 if none
        + (1.2 + 1.8 · recency_frequency_i) if mentioned   # Σ exp(−age_days / 7), log-scaled to ≤ 1; the 1.2 floor keeps your words above any base word
        + 2.0 · struggle_i              # (1 − R_i) if learned, + 0.5 per mispronunciation in 14 days (cap 1)
        + 1.0 · topic_salience_i        # share of the last 7 days' utterances in this item's topic
        + 0.4 · base_weight(level) / rank_i^0.3   # base items only; ≤ 1.0, so the base list fills gaps and never leads
        − 5.0 · already_due_or_seen_i   # avoid duplicates with today's reviews
```

`base_weight(level)` falls as the level rises — 2.5 at level 0, 1.5 at 2, 0.6 at 5 — so a beginner's
batch is roughly 60% base and an advanced learner's roughly 20%.

**Selection:** take the top items with diversity constraints (max 3 per topic, max 2 grammar items, at
least one base item while level ≤ 2), size 5–10 (default 7).

## Reasons (shown to the user)

| `reason_kind` | Template |
|---|---|
| `spoken` | "You said “mind” 9 times this week" |
| `scenario` | "For the dentist on Thursday" |
| `struggle` | "You've mispronounced this twice" / "Slipping — last seen 12 days ago" |
| `topic` | "You've been talking about neuroscience" |
| `base` | "One of the 500 most common words" |
| `grammar` | "You've said “I want that you…” — here's how Spanish does it" |

## Spaced repetition: FSRS-4.5

Once introduced, every item is a card scheduled by FSRS (Ye, Su & Cao, *A Stochastic Shortest Path
Algorithm for Optimizing Spaced Repetition Scheduling*, KDD, Aug 2022), using the FSRS-4.5 formulas
and default parameters published by the open-spaced-repetition project (2023):

- Retrievability `R(t, S) = (1 + 19/81 · t / S)^−0.5`
- Next interval for target retention 0.9: `I = S`
- Stability after success: `S' = S · (e^w8 · (11 − D) · S^−w9 · (e^(w10·(1−R)) − 1) · hardPenalty · easyBonus + 1)`
- Stability after a lapse: `S' = w11 · D^−w12 · ((S + 1)^w13 − 1) · e^(w14·(1−R))`
- Difficulty update with mean reversion toward `D0(4)`.

Parameters can be refitted per user from the `reviews` log once a user has 1,000+ reviews (P3).

## Evaluation plan

1. **Golden set:** one week of the founder's real transcripts (≈ 2,000 sentences), hand-labelled with
   "words I'd want to learn" and "topics that matter".
2. **Offline metrics:** precision@7 of batch picks against the labels; share of picks with a
   *spoken* or *scenario* reason (target ≥ 60% after week 1); duplicate rate (target 0).
3. **Online metrics:** batch open rate, "Got it" rate on first review (target 60–80% — too high means
   too easy), 30-day retention of introduced items.
4. **Prompt evals for the agents:** close-translation fidelity (alignment coverage ≥ 90% of
   source tokens), brevity (translations single-line, answers ≤ 3 sentences), no unrequested
   explanation (regex + LLM judge), run on every prompt change.
