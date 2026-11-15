# Roadmap

Estimates assume one full-time engineer using AI coding agents. Part-time roughly doubles them.

## Phase 1 — daily driver (8–10 weeks)

Goal: the founder uses it every day for Say-it-my-way and word batches.

| Week | Milestone | Features |
|---|---|---|
| 1 | Repo, docs, design system, token pipeline | — |
| 1–2 | Backend skeleton, auth, App Attest | P1, P2, P3, P4 |
| 2–3 | Say it my way (text + voice), alignment | H1, H2, H3, P9 |
| 3–4 | FSRS, word batches with reasons, base backbone | T1, T2, G1 |
| 4–6 | iOS: onboarding, Today, Say it my way, Review | H1–H3, T3, P8 |
| 6–7 | Manual scenarios + prep packs | A3, A4 |
| 7–8 | Phrasebook, settings, privacy centre, dialects | H9, P5, P10 |
| 8–10 | TestFlight hardening, crash/telemetry, bug bash | — |

**Exit criteria:** 14 consecutive days of real use; 200+ reviewed items; zero P0 security findings.

## Phase 2 — ambient + rehearsal (10–14 weeks)

| Milestone | Features |
|---|---|
| **Capture spike (do this first):** prove background capture survives lock for 8 h on current iOS | H4 |
| Ambient capture, own-voice filter, privacy controls, Moments | H4, H6, H7, H8 |
| Recurring + calendar scenarios, prep timing | A1, A2, A5 |
| Scene library: search by meaning (text or voice), use, share, report | L1, L2, L3, L4 |
| Role-play with hints, rescue drill, shadowing | R1, R2, R3, R5 |
| Pronunciation scoring (GOP on wav2vec 2.0 phonemes) | T4 |
| Notification budget, quiet hours | T5 |
| Grammar on demand, level estimate | G2, G3 |
| Confidence map, Spanglish ratio | G4, G5 |
| Quick capture surfaces, widgets, Live Activity, offline | H5, P6, P7 |

## Phase 3 — polish + App Store (8–12 weeks)

| Milestone | Features |
|---|---|
| Full visual design pass with a product designer (4–6 weeks of design time) | — |
| Passkeys, data export UI, weekly reflection | P1, P4, G6 |
| Live lifeline (AirPods), pendant input | R4, H10 |
| OWASP MASVS v2 audit + external pen test | — |
| Privacy labels, App Review, launch | — |

## Later: generative UI (to do, evaluate first)

**Idea.** Let the model compose some screens from the app's own native components instead of every layout being fixed. The model returns a description of which components to show, in what order and with what content, and the app renders it with SwiftUI and the web build's components. No code is downloaded or run.

**Check Apple's rules before starting.**

* Guideline 2.5.2 says apps must be self-contained and may not download, install or execute code that introduces or changes features or functionality. Model output that only fills and arranges components the reviewed app already has should count as content, but anything that adds functionality after review has to go through review. Apple has been enforcing this against AI app builders since March 2026.
* Guideline 2.5.19 bars hidden, dormant or undocumented features. Every layout a learner can get should be reachable by App Review in the review build.
* To stay inside both, keep a fixed catalogue of components in the binary, validate every generated description against a schema, fall back to the fixed layout when one fails, describe the renderer in the Review Notes, and ask App Review if anything is unclear.

**Decide which screens go first.** Score each candidate on how much it gains from adapting to the moment, how risky a wrong layout would be, and how content-driven it already is.

| Candidate | Why it might gain |
|---|---|
| Answers on Say | A question could come back as a short table, a conjugation grid or a side-by-side comparison instead of plain text |
| Grammar lessons | Each pattern may explain better with a different shape (a table, a timeline, paired examples) |
| Scene prep | A phone call, a meeting and a doctor's visit need different emphasis |
| Today | What to show first could follow the time of day and what's coming up |
| Rehearsal summary and weekly reflection | The highlights differ a lot from one session or week to the next |

Keep these fixed regardless: onboarding, sign-in, settings, capture and privacy controls, permissions, export and deletion, and the review session.

**Constraints.** Design tokens only, accessibility labels and Dynamic Type for everything generated, the brevity contract still applies, language comes from the language pack, and the web build renders the same descriptions.

**Status.** Not started. Evaluate after the remaining iPhone features.

## Top risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| iOS kills background capture | Ambient feature unreliable | Week-1 spike in P2; keep hold-to-talk, Action Button and pendant as first-class fallbacks |
| Spanglish recognition | Mixed sentences mis-transcribed | Detect language switches; route mixed segments to a multilingual Whisper-class model (Radford et al., *Robust Speech Recognition via Large-Scale Weak Supervision*, Dec 2022) |
| Curation feels random | Core value lost | Build an eval set from a week of real transcripts before tuning; every item carries a human-readable reason |
| LLM cost/latency | Slow translations | Route short, simple sentences on device; cache by normalised text; self-host for the founder |
| Privacy perception | Users won't enable capture | On-device transcription, own-voice filter, visible indicator, one-tap forget |

## Commit plan (this repository)

Each feature lands as its own commit, in this order:

1. `docs:` product vision, feature list, roadmap
2. `design:` UX flows, screen specs, design system spec
3. `design:` OKLCH token generator + generated tokens + prototype
4. `docs:` architecture, security, data model, API, curation engine
5. `feat(backend):` scaffold → auth → App Attest → translate → capture → FSRS → batches → scenarios → rehearsal → pronunciation → progress
6. `feat(ios):` project + kit → design system → onboarding → Today → Say it my way → Review → Scenarios → Rehearse → Progress → Settings
