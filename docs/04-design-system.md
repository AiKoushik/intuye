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
   drops below. Current result: **108 checks, 0 failing** — see
   [`design/tokens/build/contrast-report.md`](../design/tokens/build/contrast-report.md).
5. **Four appearances per token:** light, dark, light + high contrast, dark + high contrast, shipped as
   Display P3 colour sets in `Assets.xcassets`.

Pipeline: `design/tokens/source.json` → `generate.py` → asset catalog + `ColorTokens.swift` +
`tokens.css` + report.

### Families

| Family | Hue | Meaning | Why this hue |
|---|---|---|---|
| **Ink** | 262° (blue-black, very low chroma) | Text, surfaces, borders | Writing ink, so your words read like your own handwriting |
| **Azulejo** | 270° ultramarine | The only accent: actions, links, alignment threads | The blue of Spanish tilework; deeper and more violet than iOS default blue, so it doesn't read as "untinted" |
| **Azafrán** | 80° saffron | The highlighter on new words; attention | A highlighter pen marks what's new, and saffron is unmistakably Spanish without flag clichés |
| **Olivo** | 135° olive | Success, *Got it* | Calm rather than neon "success green" |
| **Granada** | 24° pomegranate | Errors, *Forgot* | Warm red that sits with saffron instead of fighting it |

### Semantic tokens (use these, never ramps, in code)

| Token | Light | Dark | Use |
|---|---|---|---|
| `canvas` | `#F8FAFE` | `#0C0D0F` | Screen background |
| `surface` | `#FFFFFF` | `#151619` | Cards, sheets |
| `sunken` | `#F1F3F7` | `#0E1015` | Input wells, grouped areas |
| `textPrimary` | `#151619` | `#F8FAFE` | Spanish lines, titles, body |
| `textSecondary` | `#5E636C` | `#BABEC5` | Your words (source line), captions |
| `textTertiary` | `#7B808B` | `#9A9FA7` | Large hints, placeholders only |
| `hairline` | `#E5E8ED` | `#202225` | Dividers (decorative) |
| `borderStrong` | `#7B808B` | `#5E636C` | Input borders, control outlines |
| `accent` | `#3E55C8` | `#A4BBFF` | Links, tinted text, icons |
| `accentFill` / `onAccent` | `#3E55C8` / white | `#7997FF` / ink | Primary buttons |
| `accentSubtle` | `#EFF3FF` | `#121C4B` | Selected rows, coach bubbles |
| `highlight` / `onHighlight` | `#F2D39E` / ink | `#4B3300` / white | New-word mark, paired-word mark |
| `success` | `#34591B` | `#A6CA93` | Got it, readiness up |
| `warning` | `#664700` | `#E0B771` | Attention |
| `danger` | `#AD2F32` | `#FFA09A` | Forgot, errors, destructive |
| `focusRing` | `#5471F7` | `#A4BBFF` | Keyboard / Full Keyboard Access focus |

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
