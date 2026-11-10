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
