# Design system

Native SwiftUI on iOS 26+, following Apple's Human Interface Guidelines and Liquid Glass materials.
The identity comes from three choices: **ink and tile** colour, **two voices** in type, and the
**interlinear line** as the signature component.

## Colour

### Method

1. **Defined in OKLCH.** Every hue family is a tonal ramp with the same lightness steps, so `500` in
   one family looks as light as `500` in any other (Ottosson, *A perceptual color space for image
   processing*, Dec 2020). This is what lets us swap a hue without re-checking every screen by eye.
2. **Chroma follows an envelope** — highest at mid-lightness, tapering towards white and black — so the
   lightest tints never go neon and the darkest shades never go muddy.
3. **Gamut-mapped twice.** Each colour is mapped into Display P3 (what iPhones show) and separately into
   sRGB (fallback and contrast maths) by reducing chroma at constant lightness and hue, the CSS Color 4
   approach.
4. **Contrast-checked automatically** against WCAG 2.2 (W3C, Oct 2023): text 4.5:1, large text and UI
   3:1; in Increase Contrast mode, 7:1 and 4.5:1. `generate.py --check` fails the build if any pair
   drops below. Current result: **344 checks, 0 failing** — see
   [`design/tokens/build/contrast-report.md`](../design/tokens/build/contrast-report.md).
5. **Four appearances per token:** light, dark, light + high contrast, dark + high contrast, shipped as
   Display P3 colour sets in `Assets.xcassets`.

Pipeline: `design/tokens/source.json` → `generate.py` → asset catalog + `ColorTokens.swift` +
`tokens.css` + report.

### Layers, not flat white or black

Every screen is built from lightness layers so cards, sheets and wells separate without heavy borders:

| Layer | Light (L) | Dark (L) |
|---|---|---|
| Well (`sunken`) | 0.93 | 0.19 |
| Page (`canvas`) | 0.95, soft mist | 0.22, deep slate |
| Card (`surface`, or a tint `Wash`) | 0.99 | 0.26 |
| Sheet (`surfaceRaised`) | 1.00 | 0.30 |

Text stops short of the extremes: body text is L 0.26 on the light page (13.7:1) and L 0.94 on the
dark page (14.5:1), well past WCAG's 4.5:1 without the glare of black on white or the halo of white
on black. Each screen carries a faint glow at the top, mixed from two tints' `Ambient` strength
(Today: sand + rose; Say: sea + plum; Scenes: sage + sea; Progress: plum + sea; Review: sea + sage;
Rehearse: sage + sand), and cards that hold a particular kind of thing sit on that tint's `Wash`
(the next scene, today's words, rescue phrases, what you'll hear, your Spanglish trend, answers).

### Families

| Family | Hue | Meaning | Why this hue |
|---|---|---|---|
| **Ink** | 262° (blue-black, very low chroma) | Text, surfaces, borders | Writing ink, so your words read like your own handwriting |
| **Azulejo** | 270° ultramarine | The only accent: things you can tap (actions, links, the mic) | The blue of Spanish tilework; deeper and more violet than iOS default blue, so it doesn't read as "untinted" |
| **Azafrán** | 80° saffron | The highlighter on new words; attention | A highlighter pen marks what's new, and saffron is unmistakably Spanish without flag clichés |
| **Olivo** | 135° olive | Success, *Got it* | Calm rather than neon "success green" |
| **Granada** | 24° pomegranate | Errors, *Forgot* | Warm red that sits with saffron instead of fighting it |

### Sober tints

Five quiet families on the same lightness scale, each in four strengths from one recipe: text (L 0.43 / 0.83), subtle for chips and tiles (L 0.91 / 0.34), wash for cards (L 0.97 / 0.27) and ambient for the screen glow (L 0.90 / 0.30). They say
**what something is about** or **why it's here**, never "tap me", and always sit next to a label. A
tint's text on its own chip is 6.1:1 or better in light mode and 7.1:1 in dark; body text on any wash
is 12:1 or better.

| Tint | Hue | Scenes about | Why a word is here | Also |
|---|---|---|---|---|
| **Salvia** (`sage`) | 150° sage | Health and body | For a scene coming up | Rehearsal partner's bubbles |
| **Mar** (`sea`) | 215° slate sea | Work and study | You said it | English → Spanish label, "words ready" |
| **Arena** (`sand`) | 78° sand | Home and family | Core Spanish for your level | "You asked" label, "Heard at" stamps |
| **Rosa** (`rose`) | 12° dusty rose | Food and friends | You keep missing it | Notifications row |
| **Ciruela** (`plum`) | 320° plum | Travel and errands | A topic you talk about | Spanish → English label, the Spanglish trend line |

A scene's tint comes from its topic, then its title (keyword match), falling back to a stable hash
of the text. Readiness dots take the scene's tint. Code: `Tint` in `DesignSystem/Tint.swift`, `.t-*`
classes in the web build.

### Semantic tokens (use these, never ramps, in code)

| Token | Light | Dark | Use |
|---|---|---|---|
| `canvas` | `#EBEFF6` (L 0.95) | `#151A21` (L 0.21) | The page, under everything (light: a soft mist, not white; dark: deep slate, not black) |
| `surface` | `#FAFCFE` (L 0.99) | `#1F252D` (L 0.26) | Cards, grouped rows: one layer above the page |
| `surfaceRaised` | `#FDFEFF` (L 1.00) | `#282E38` (L 0.30) | Sheets and popovers: one more layer |
| `sunken` | `#E2E8EF` (L 0.93) | `#0F141A` (L 0.19) | Input wells, segmented controls |
| `textPrimary` | `#1C232E` (L 0.26) | `#E6EAEF` (L 0.94) | Spanish lines, titles, body (never pure black or white) |
| `textSecondary` | `#4F5763` (L 0.46) | `#B0B6C0` (L 0.78) | Your words (source line), captions |
| `textTertiary` | `#69717C` (L 0.55) | `#8E949E` (L 0.67) | Large hints, placeholders only |
| `hairline` | `#D2D8E1` (L 0.88) | `#303741` (L 0.34) | Dividers (decorative) |
| `borderStrong` | `#727B88` (L 0.58) | `#737B86` (L 0.58) | Input borders, control outlines |
| `accent` | `#3A55B1` (L 0.48) | `#A3BCFC` (L 0.80) | Links, tappable text and icons |
| `accentFill` | `#3A55B1` (L 0.48) | `#93AEF8` (L 0.76) | Primary buttons |
| `onAccent` | `#FAFCFF` (L 0.99) | `#101524` (L 0.20) | Text on primary buttons |
| `accentSubtle` | `#D6E2FE` (L 0.91) | `#283350` (L 0.33) | Secondary buttons, selected rows |
| `highlight` | `#F4D397` (L 0.88) | `#644B18` (L 0.43) | New-word mark, paired-word mark |
| `onHighlight` | `#1C232E` (L 0.26) | `#EFF2F6` (L 0.96) | Text on the highlight |
| `success` | `#345F2A` (L 0.44) | `#A2D098` (L 0.81) | Got it, readiness up |
| `warning` | `#755010` (L 0.46) | `#E6C183` (L 0.83) | Attention |
| `danger` | `#A53332` (L 0.49) | `#F19E97` (L 0.78) | Forgot, errors, destructive |
| `focusRing` | `#4F6DCC` (L 0.56) | `#99B5FE` (L 0.78) | Keyboard / Full Keyboard Access focus |
| `sage` / `Subtle` / `Wash` / `Ambient` | `#325B3B` / `#CFEAD4` / `#ECF9ED` / `#C5E9CB` | `#ACD3B3` / `#243E29` / `#1C2B1F` / `#1E3422` | Text, chips, cards, screen glow |
| `sea` / `Subtle` / `Wash` / `Ambient` | `#115968` / `#C3EAF4` / `#E6F8FD` / `#B5E8F5` | `#9BD2E0` / `#133D46` / `#142B30` / `#10333B` | Text, chips, cards, screen glow |
| `sand` / `Subtle` / `Wash` / `Ambient` | `#654B1E` / `#F2DFC3` / `#FCF3E6` / `#F3DAB6` | `#DDC39C` / `#443318` / `#2F2516` / `#392B14` | Text, chips, cards, screen glow |
| `rose` / `Subtle` / `Wash` / `Ambient` | `#713F45` / `#FDD7DA` / `#FFF0F1` / `#FFD0D5` | `#ECB8BD` / `#4C2C30` / `#342123` / `#402528` | Text, chips, cards, screen glow |
| `plum` / `Subtle` / `Wash` / `Ambient` | `#614368` / `#EFD9F4` / `#FBF0FD` / `#EFD3F5` | `#D9BBE0` / `#422E46` / `#2E2230` / `#37273B` | Text, chips, cards, screen glow |

**Rule:** colour is never the only signal. Rating buttons pair colour with a label and an SF Symbol;
new words pair the highlight with VoiceOver "new word".

## Typography: two voices

| Role | Face | Why |
|---|---|---|
| UI, your words | **SF Pro** (system) | Native, legible at every Dynamic Type size |
| Spanish lines, coach speech | **New York** (system serif, `.serif` design) | Gives Spanish its own voice, a slightly literary one, clearly distinct from the UI |

Both are system faces, so Dynamic Type, optical sizing and localisation come free, with no licensing.

### Scale (maps to Dynamic Type styles; sizes shown at the default "Large" setting)

| Token | Text style | Face | Size / leading | Weight | Use |
|---|---|---|---|---|---|
| `display` | `.largeTitle` | SF Pro | 34 / 41 | Bold | Tab titles |
| `spanishXL` | `.title` | New York | 28 / 34 | Regular | Review card back, hero Spanish |
| `spanish` | `.title3` | New York | 20 / 25 | Regular | Interlinear Spanish line |
| `headline` | `.headline` | SF Pro | 17 / 22 | Semibold | Card titles |
| `body` | `.body` | SF Pro | 17 / 22 | Regular | Body |
| `source` | `.callout` | SF Pro | 16 / 21 | Regular | Interlinear source line (your words) |
| `caption` | `.footnote` | SF Pro | 13 / 18 | Regular | Reasons, metadata |

Sentence case everywhere. No all-caps labels. Numbers use tabular figures where they change in place.

## Space, shape, depth

- **Spacing:** 4-pt grid — `xs 4 · s 8 · m 12 · l 16 · xl 24 · xxl 32 · xxxl 48`. Screen margins 20 pt.
- **Radii by hierarchy (continuous corners):** sheets 28 · cards 20 · controls 12 · chips capsule.
  Nested radius = outer − padding, so corners stay concentric.
- **Depth:** system materials (Liquid Glass for tab bar and accessory, `.regularMaterial` sheets).
  Cards are flat `surface` on `canvas` with a `hairline` stroke; no drop shadows.

## Motion and haptics

| Moment | Motion | Haptic |
|---|---|---|
| Tap a word (pair lights up) | Highlight grows from the word baseline, 180 ms ease-out | `.selection` |
| Hold-to-talk press | Button scales 0.96, mic ring pulses with input level | `.impact(.soft)` on press and release |
| Result arrives | Spanish line resolves from shimmer; spring (response 0.35, damping 0.85) | none |
| Rating | Card slides away in the direction of the rating | `.success` for Got it / Easy |
| Forget last 10 min | Rows collapse | `.warning` |

**Reduce Motion:** springs and slides become 150 ms cross-fades; the shimmer and mic pulse become static.

## Iconography

SF Symbols only, matched to text weight. Key symbols: `waveform` (capture), `mic.fill` (hold to
talk), `text.bubble` (Say), `theatermasks` (Scenes), `chart.line.uptrend.xyaxis` (Progress),
`star` (save), `lifepreserver` (rescue phrases), `calendar` (upcoming).

## Components

| Component | Anatomy | Notes |
|---|---|---|
| **InterlinearLine** | Source tokens row (SF Pro, secondary) over target tokens row (New York, primary); alignment links | Wraps by alignment group so pairs never split across lines; tap highlights pair with `highlight`; `is_new` tokens carry a persistent underline mark |
| **ResultCard** | InterlinearLine, direction chip, save star, optional "More natural" disclosure | Brief by default: no explanation text unless the user asked |
| **AnswerCard** | Plain text, ≤ 3 sentences | Only for explicit questions |
| **HoldToTalkButton** | 64-pt circle, level ring | Long-press gesture; VoiceOver: double-tap to start, double-tap to stop |
| **WordChip** | Capsule, Spanish word, optional new mark | — |
| **ReviewCard** | Cue, context, reveal, reason | Four `RatingButton`s below |
| **RatingButton** | Label + symbol + semantic colour | Forgot (`danger`), Hard (`warning`), Got it (`success`), Easy (`accent`) |
| **ReadinessDots** | 5 dots, filled to rating | Value read by VoiceOver as "3 of 5" |
| **SceneRow** | Title, due label, ReadinessDots | — |
| **CoachBubble / YouBubble** | Serif Spanish / SF Pro | Coach bubble tap reveals English close line |
| **CapturePill** | Bottom accessory: status dot + label + count | Dot is also shape-coded (filled = on, ring = off) |

## Prototype

`design/prototype/index.html` is a clickable, phone-sized prototype of the key screens using the
generated `tokens.css`. Tap words in the interlinear lines; flip the review card; toggle dark mode.
