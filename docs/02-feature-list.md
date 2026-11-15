# Feature list

Each feature has an ID, the loop stage it belongs to, a phase, a MoSCoW priority, and a happy-path
acceptance test. ★ marks features no app in our competitor scan (Langua, Fully Fluent, LexiCard,
Langotalk, ensemble, Omi, Google Translate Practice) offers.

**Phases:** P1 = daily-driver MVP (8–10 weeks) · P2 = ambient + rehearsal (10–14 weeks) ·
P3 = polish + App Store (8–12 weeks). See [10-roadmap.md](10-roadmap.md).

**Status key:** ✅ built (happy path) · 🟡 partial · ⬜ planned. Backend items are tested; iOS items are written but not yet compiled (needs a Mac with Xcode).

## Hear — capture what you want to say

| ID | Feature | Phase | Priority | Happy-path acceptance | Status |
|---|---|---|---|---|---|
| H1 | ★ **Say it my way (text, both directions)** — English/Spanglish → Spanish and Spanish → English, kept as close to your sentence as grammar allows; one line, no explanation. A natural variant only when the close one sounds wrong, collapsed | P1 | Must | "me gusta escuchar este en mi mind" → "Me gusta escuchar esto en mi mente" (`mind → mente` new); "como te va" → "How's it going?" | ✅ |
| H11 | ★ **Ask** — explicit language questions ("tú or usted with my landlord?", "what do I say at a pharmacy?") get a short answer covering only what was asked | P1 | Must | "when do I use usted?" → ≤ 3 sentences, no unrequested extras; plain translations never include explanations | ✅ |
| H2 | **Say it my way (voice)** — hold to talk, on-device transcription, same result | P1 | Must | Holding the mic, speaking, releasing shows the result in < 2 s after release | ✅ |
| H3 | ★ **Word alignment** — tap any word to see its pair; new-to-you words highlighted | P1 | Must | Each source token maps to zero or more target tokens; unknown words flagged `is_new` | ✅ |
| H4 | ★ **Ambient capture** — always-on or scheduled windows; transcribes your sentences in the background | P2 | Must | With capture on and phone locked, sentences spoken over 10 min appear in Moments | 🟡 no own-voice filter yet |
| H5 | **Quick capture** — Action Button, Lock Screen and Control Center controls, Siri "How do I say…" App Intent | P2 | Should | Pressing the Action Button starts hold-to-talk without opening the app | ⬜ |
| H6 | ★ **Own-voice filter** — 30-second enrolment; only your voice is kept | P2 | Must | Background TV speech isn't stored | ⬜ |
| H7 | **Privacy controls** — pause, "forget last 10 minutes", auto-delete after N days, never-record places | P2 | Must | "Forget last 10 min" removes those utterances locally and on the server | 🟡 pause + forget; no places |
| H8 | **Moments** — day timeline of captured sentences; swipe to save or delete | P2 | Should | Today's moments render grouped by hour | 🟡 web build + API; iPhone screen ⬜ |
| H9 | **Phrasebook** — saved sentences with audio, searchable | P1 | Should | Saving a translation adds it to the Phrasebook | ✅ on device |
| H10 | Pendant / Bluetooth mic input (e.g. Omi) | P3 | Could | Pendant audio flows into the same pipeline | ⬜ |

## Anticipate — know what's coming

| ID | Feature | Phase | Priority | Happy-path acceptance | Status |
|---|---|---|---|---|---|
| A1 | ★ **Recurring scenarios** — topics you keep talking about become scenarios (e.g. "neuroscience", "cooking") | P2 | Must | 3+ utterances on a topic within 7 days creates a suggested scenario | ✅ |
| A2 | ★ **Upcoming scenarios from Calendar** — opt-in; titles read on device, only title, time and a category sent | P2 | Must | "Dentist Thu 10:00" creates a "At the dentist" scenario due Wed evening | ✅ |
| A3 | **"I have this coming up"** — create a scenario by typing or saying it, with optional details; the scene builder agent drafts the pack | P1 | Must | "Parent-teacher meeting next week" creates a scenario with a prep pack | ✅ |
| A4 | ★ **Prep pack** — 8–12 key phrases, likely questions you'll hear, rescue phrases | P1 | Must | Every scenario has a pack with at least 8 phrases and 3 rescue phrases | ✅ |
| A5 | **Prep timing** — reminder the evening before or 2 h before | P2 | Should | A calendar scenario schedules one reminder within the notification budget | ✅ server plan: evening before and 2 h before, moved out of quiet hours |

## Library — scenes other learners have built

| ID | Feature | Phase | Priority | Happy-path acceptance | Status |
|---|---|---|---|---|---|
| L1 | ★ **Scene library search** — find a scene by typing or saying it; matching is by meaning (vector search), not keywords, and only shows scenes in your Spanish variety | P1 | Must | "going to the dentist's" finds "At the dentist" | ✅ |
| L2 | **Use a library scene** — add a ready-made scene with its prep pack at once, no waiting for generation | P1 | Must | Using "At the dentist" creates your scene with ≥ 8 key phrases and counts one more use | ✅ |
| L3 | ★ **Share new scenes** — a scene you build is generalised (names, places and other personal details removed) and added to the library only if nothing the same or similar is there; anonymous by default, your name only if you choose | P1 | Must | Building "At the dentist's" when "At the dentist" exists adds nothing and links yours to it; an anonymous share stores no link to you | ✅ |
| L4 | **Report a scene** — any learner can report a library scene; three reports hide it until reviewed (App Store guideline 1.2) | P1 | Must | The third report hides the scene from search | ✅ |

## Rehearse — practise the exact moment

| ID | Feature | Phase | Priority | Happy-path acceptance | Status |
|---|---|---|---|---|---|
| R1 | **Voice role-play** — the coach plays the other person; difficulty dial (gentle / real / fast) | P2 | Must | A 6-turn dentist role-play completes with a summary | ✅ |
| R2 | **Hints and escape hatch** — "say it in English" any time, get the Spanish back | P2 | Must | Saying an English line mid-role-play returns its Spanish and continues | ✅ |
| R3 | ★ **Rescue-phrase drill** — "¿Puede repetir?", "Más despacio, por favor", "¿Cómo se dice…?" | P2 | Should | Drill covers the pack's rescue phrases with speak-to-answer | ✅ |
| R4 | ★ **Live lifeline** — whisper "¿cómo se dice…?" in a real conversation, hear the word in AirPods | P3 | Could | Whispered English word returns Spanish audio in < 1.5 s | ⬜ |
| R5 | **Shadowing** — listen, repeat, compare | P2 | Should | Word-level match shown after each attempt | ✅ |

## Retain — keep what you learn

| ID | Feature | Phase | Priority | Happy-path acceptance | Status |
|---|---|---|---|---|---|
| T1 | ★ **Word batches with reasons** — 5–10 items, each with a why ("you said *mind* 9× this week") | P1 | Must | Batch returns 5–10 items, each with a non-empty reason and source | ✅ |
| T2 | **FSRS scheduling** — every item reviewed at its optimal moment | P1 | Must | Rating "Good" on a new item schedules the next review days later; "Again" schedules it sooner | ✅ |
| T3 | **Review session** — see English → recall → reveal → rate; or speak the answer | P1 | Must | A 10-card session completes and updates every card's schedule | ✅ |
| T4 | **Pronunciation feedback** — per-word score; misses feed the next batch | P2 | Must | A mispronounced word gets a lower score and reappears in the next batch | ✅ phoneme-level from transcripts (rule-based Spanish G2P); acoustic GOP ⬜ |
| T5 | **Notification budget** — max 3/day, quiet hours 22:00–08:00 by default | P2 | Must | A 4th notification in a day is suppressed | ✅ one planner for scenes, reviews and the Monday card; one an hour; each says why |

## Grow — raise the level, not just the niche

| ID | Feature | Phase | Priority | Happy-path acceptance | Status |
|---|---|---|---|---|---|
| G1 | ★ **Base backbone** — high-frequency core blended in by level (beginner ≈ 60% base, advanced ≈ 20%) | P1 | Must | A new user's first batch contains base items; base share falls as level rises | ✅ |
| G2 | ★ **Grammar on demand** — patterns in your own sentences trigger 60-second micro-lessons | P2 | Should | "I want that you come" → subjunctive micro-lesson | ✅ 7 hand-written lessons; from review cards and Progress |
| G3 | **Level estimate** — rough CEFR band from vocabulary known and sentence complexity | P2 | Should | Level updates weekly | ✅ on Progress, with "Use this level" |
| G4 | ★ **Confidence map** — can-do rating per scenario, before and after rehearsal | P2 | Must | Each rehearsed scenario shows before/after ratings | ✅ |
| G5 | ★ **Spanglish ratio** — share of English in your Spanish attempts, trended weekly | P2 | Must | Progress shows this week vs last week | ✅ |
| G6 | **Weekly reflection** — one calm summary card, no guilt | P3 | Should | Monday card summarises the past week | ✅ Today on Mondays, Progress always |

## Platform — account, security, quality

| ID | Feature | Phase | Priority | Happy-path acceptance | Status |
|---|---|---|---|---|---|
| P1 | **Sign in with Apple** (+ passkeys in P3) | P1 | Must | Apple identity token → account + session | ✅ SIWA (passkeys P3) |
| P2 | **Session security** — 10-min access tokens, rotating refresh tokens with reuse detection, Keychain storage | P1 | Must | Refresh returns a new pair; reusing an old refresh token revokes the family | ✅ |
| P3 | **App Attest on every call** — only the genuine app can call the API | P1 | Must | Valid assertion passes; tampered signature is rejected | ✅ |
| P4 | **Account deletion and data export** (App Store 5.1.1(v)) | P1 | Must | Delete removes all user rows; export returns JSON of all user data | ✅ |
| P5 | **Dialect choice** — Spain, Mexico, neutral Latin American | P1 | Should | Translations follow the chosen variety (e.g. *ordenador* vs *computadora*) | ✅ |
| P6 | **Offline mode** — queue utterances, run reviews offline, sync later | P2 | Should | Airplane-mode reviews sync on reconnect | ✅ capture queue, offline reviews replayed with their real time |
| P7 | **Widgets + Live Activity** — today's batch widget; capture status in the Dynamic Island | P2 | Should | Widget shows due count | ⬜ |
| P8 | **Accessibility** — Dynamic Type to AX5, VoiceOver labels, Reduce Motion, no colour-only states | P1 | Must | Every screen usable at AX3 with VoiceOver | 🟡 built in, not audited |
| P9 | **Model routing** — every agent runs on LangChain Deep Agents (LangGraph underneath) over a provider-agnostic chat model: self-hosted (OpenAI-compatible, e.g. Hearth) or cloud; on-device Apple model for short offline translations | P1 | Should | Switching `LLM_PROVIDER` changes the backend model with no code change | ✅ backend; on-device ⬜ |
| P10 | **Settings and privacy centre** — what's stored, where, and delete controls | P1 | Must | Settings lists data categories with delete actions | ✅ |

## What we deliberately left out

Leaderboards, hearts/lives, gems, ads, and a fixed unit path. See
[01-product-vision.md](01-product-vision.md#non-goals).
