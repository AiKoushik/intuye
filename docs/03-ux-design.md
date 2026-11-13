# UX design

## Design concept: the interlinear line

The memorable thing in LangCoach is one element, used everywhere: **the interlinear line.** Your
sentence sits on top in the UI face; the Spanish sits directly beneath it in a serif; tapping any word
lights up its partner in the other line with a saffron highlighter mark. Linguists have glossed
languages this way for centuries (the Leipzig Glossing Rules standardise it); we make it tappable.

```
  me gusta  escuchar  este   en   mi   mind          ← your words (SF Pro, secondary ink)
     │         │        │     │    │     │
  Me gusta  escuchar  esto   en   mi  ▓mente▓        ← Spanish (New York serif, primary ink)
                                       └ new word: saffron highlight
```

Everything else stays quiet: system materials, one accent colour, generous space. Boldness is spent on
the interlinear line only.

## Information architecture

```
Tab bar (Liquid Glass)                     Bottom accessory (persistent)
├── Today      — what's next for you       ┌───────────────────────────────┐
├── Say        — say it my way + ask       │ ● Listening   14 sentences  ▢ │  tap: capture controls
├── Scenes     — situations coming up      └───────────────────────────────┘  long-press: hold to talk
└── Progress   — confidence map, ratio
Profile button (Today header) → Settings & privacy centre
```

Four tabs, because there are four questions the user brings: *What should I do now? How do I say
this? Am I ready for Thursday? Am I getting better?* Settings is not a tab; it is rarely visited.

The bottom accessory (`tabViewBottomAccessory`, iOS 26) is the capture surface: always visible,
always honest about whether the mic is on.

## Voice and copy

- **Brief.** Translations are one line. No "Great job!", no explanation unless asked.
- **Plain verbs, sentence case.** "Start review", "Rehearse", "Save to phrasebook".
- **Reasons, not nags.** "Dentist tomorrow — 6 phrases ready" not "Don't lose your streak!"
- **Mistakes are mirrors.** "A native would say: *Más despacio, por favor*" not "Wrong".
- **Rating labels say what happened:** *Forgot · Hard · Got it · Easy* (mapped to FSRS Again/Hard/Good/Easy).

## Core flows

### 1. First run (under 60 seconds to first value)

```
Welcome ─► Pick your Spanish ─► Rough level ─► Sign in with Apple ─► Say tab (first sentence)
 (one        (Spain / Mexico /     (Just starting /                      mic permission asked
 interlinear  Latin America)        I get by /                           only when they first
 example)                           Conversational)                      press the mic
```

Permissions are asked **in context**, never in onboarding: microphone on first hold-to-talk,
calendar on "Use my calendar" in Scenes, notifications after the first completed batch.

### 2. Say it my way (H1, H2, H3, H11)

```
Say tab ─► hold mic (or type) ─► release ─► interlinear result ─► [tap word: pair lights up]
                                                │                 [☆ save to phrasebook]
                                                │                 [▸ more natural (collapsed, only if different)]
                                                └─ if input is a question about Spanish → short Answer block
```

Direction is detected automatically: English or Spanglish → Spanish; Spanish → English. A small chip
shows it ("English → Spanish") and can be tapped to force the other way.

### 3. Word batch review (T1, T2, T3)

```
Today: "Your words · 7 ready" ─► card: English cue + your original sentence as context
     ─► tap "Show" (or hold mic and say it) ─► Spanish revealed, why-this-word line
     ─► Forgot / Hard / Got it / Easy ─► next card ─► summary: "7 words, next review Thu"
```

### 4. Scenario prep and rehearsal (A3, A4, R1, R2, G4)

```
Scenes ─► "Find or add a scene" (type, or hold the mic and say it)
       ─► library results by meaning ─► "Use this scene" ─► prep pack at once
       ─► or "Build my own" ─► title + optional details ─► Share with other learners (on) · Show my name (off)
       ─► prep pack generated ─► "Added to the library, anonymously" | "Already in the library as …" | "Kept private"
       ─► rate readiness (1–5) ─► phrases (interlinear) ─► rescue phrases ─► Rehearse
       ─► voice role-play (coach speaks Spanish; tap bubble for English; "say it in English" any time)
       ─► summary + rate readiness again ─► confidence map updates
```

### 5. Ambient capture (H4, H6, H7)

```
Accessory pill ─► capture sheet: Off / Windows (e.g. 9–12, 18–21) / Always
              ─► "Forget last 10 minutes" (one tap, confirms with haptic + toast "Forgot 10 minutes")
              ─► own-voice status, sentences today
```

## Screen specs

### Today
- **Header:** date, greeting with first name, profile button (top right).
- **Coming up** — the nearest scenario: title, when, readiness ring (1–5), primary action *Prep* or
  *Rehearse*.
- **Your words** — count ready, the first three words as chips, *Start review*.
- **Recent sentences** — last three interlinear snippets from Say or capture; tap opens in Say.
- **Empty state (day one):** "Say anything in English to get started" + *Open Say*.

### Say
- Top: direction chip. Middle: conversation-style list of results (newest at bottom). Bottom: text
  field with a large hold-to-talk button beside it (minimum 64 pt target).
- **Result card:** interlinear line; tap any token pairs it; ☆ saves; "More natural" disclosure only
  when the server returns one.
- **Answer card** (for questions): plain text, three sentences maximum, no headings.
- **Loading:** the source line appears instantly (from on-device transcription); the Spanish line
  shimmers in place, then resolves.
- **Error:** "Couldn't reach the coach. Your sentence is saved and will translate when you're back
  online." with *Retry*.

### Review
- Full-screen card stack. Front: English cue (large), context sentence (secondary, with the word
  blanked). Back: Spanish (serif, large), reason line ("You said *mind* 9 times this week").
- Bottom: four rating buttons, each with label + SF Symbol + colour (never colour alone).
- Swipe gestures are an accelerator only, not the sole path.

### Scenes
- Top: **Find or add a scene** search field with a mic button. Typing or speaking shows library
  matches (title, one-line situation, "used by 214"); the last row is always **Build "…"** with the
  exact words typed. Each result has a report option in its menu.
- Sections: **Upcoming** (from calendar, dated), **Recurring** (from your topics), **Yours**
  (manual). Each row: title, readiness dots, due label.
- New scene sheet: title, optional details ("the teacher only speaks Spanish"), **Share with other
  learners** (on; footnote: "We remove names and places first. Only shared if it's not already in
  the library."), **Show my name** (off). Calendar scenes are never shared.
- Scene detail: readiness slider, "Key phrases" (interlinear list), "If you get stuck" (rescue
  phrases), "You might hear" (likely questions), primary *Rehearse*.

### Rehearse
- Chat layout. Coach bubbles: Spanish in serif; tap reveals the English close line beneath.
- User bubbles: what you said (transcribed), with any correction offered as "A native would say…".
- Controls: hold-to-talk, *Hint*, *Say it in English*, difficulty (Gentle / Real / Fast).
- End sheet: what went well (one line), 3 phrases to keep, readiness re-rating.

### Progress
- **Confidence map:** each scene as a row with before → after readiness.
- **Spanglish ratio:** weekly line, this week vs last.
- **Words:** introduced, retained (R ≥ 0.9), due today.

### Settings and privacy centre
- Your Spanish (dialect), level.
- Capture: mode, windows, own voice re-enrol, never-record places.
- Notifications: daily budget (default 3), quiet hours (22:00–08:00).
- Your data: what's stored and where, export, delete moments older than N days, delete account.

## States checklist (every screen)

| State | Treatment |
|---|---|
| Empty | One sentence + one action, never a mascot |
| Loading | Skeleton in the final layout; no spinners for < 300 ms |
| Offline | Work continues; banner "Offline — will sync" only when an action needs the server |
| Error | Says what failed and what to do; keeps user input |
| Permission denied | Explains what doesn't work and links to Settings |

## Notifications

| Trigger | Copy example | Timing |
|---|---|---|
| Batch ready | "7 words from your week, including *mente*" | Next free slot outside quiet hours |
| Scenario soon | "Dentist tomorrow — 6 phrases ready" | Evening before, or 2 h before |
| Weekly reflection | "312 sentences this week, 41% in Spanish" | Monday 09:00 |

Hard cap: 3 per day (user adjustable 0–6). Quiet hours respected. Never more than one per hour.

## Accessibility

- All text uses Dynamic Type text styles; layouts reflow to vertical stacks at accessibility sizes.
- Interlinear line: VoiceOver reads each pair as "mind, Spanish: mente, new word".
- Rating buttons and readiness use label + icon + colour.
- Reduce Motion: spring transitions become cross-fades; shimmer becomes a static placeholder.
- Minimum hit target 44 × 44 pt; hold-to-talk 64 pt.
