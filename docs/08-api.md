# API

Base path `/v1`. JSON in and out. Every endpoint except `/health`, `/v1/attest/challenge` and
`/v1/attest/register` requires App Attest headers (`X-LC-Key-Id`, `X-LC-Assertion`,
`X-LC-Timestamp`); every endpoint except those and `/v1/auth/*` also requires
`Authorization: Bearer <access token>`. Errors: `{"error": {"code": "...", "message": "..."}}`.

## Auth and device

| Method | Path | Body → Response |
|---|---|---|
| GET | `/v1/attest/challenge` | → `{challenge}` (base64url) |
| POST | `/v1/attest/register` | `{key_id, attestation, challenge}` → `{ok: true}` |
| POST | `/v1/auth/apple` | `{identity_token, raw_nonce, display_name?}` → `{access_token, refresh_token, expires_in, user}` |
| POST | `/v1/auth/refresh` | `{refresh_token}` → new pair |
| POST | `/v1/auth/logout` | `{refresh_token}` → `204` (revokes the family) |
| GET | `/v1/me` | → `{user, settings}` |
| PATCH | `/v1/me/settings` | partial settings → settings |
| GET | `/v1/account/export` | → all user data |
| DELETE | `/v1/account` | → `204` |

## Say it my way and Ask — `POST /v1/coach`

```json
// request
{ "text": "me gusta escuchar este en mi mind", "direction": "auto" }
// response (translation)
{
  "intent": "to_es",
  "source": "me gusta escuchar este en mi mind",
  "close": "Me gusta escuchar esto en mi mente.",
  "natural": null,
  "alignment": [
    {"src": "me gusta", "tgt": "Me gusta", "new": false},
    {"src": "escuchar", "tgt": "escuchar", "new": false},
    {"src": "este", "tgt": "esto", "new": false},
    {"src": "en", "tgt": "en", "new": false},
    {"src": "mi", "tgt": "mi", "new": false},
    {"src": "mind", "tgt": "mente", "new": true}
  ],
  "answer": null,
  "utterance_id": "…"
}
```

`direction`: `auto` | `to_es` | `to_en`. For `"como te va"` the response has `intent: "to_en"`,
`close: "How's it going?"`. For an explicit question (`"when do I use usted?"`), `intent: "ask"`,
`answer` is set (≤ 3 sentences) and `close`/`alignment` are empty.

## Capture

| Method | Path | Body → Response |
|---|---|---|
| POST | `/v1/utterances` | `{items: [{text, spoken_at, source}]}` (≤ 200) → `{accepted, lexemes_touched, suggested_scenarios}` |
| GET | `/v1/utterances?day=YYYY-MM-DD` | → moments for the day |
| POST | `/v1/utterances/forget` | `{minutes}` → `{deleted}` |
| DELETE | `/v1/utterances/{id}` | → `204` |

## Words

| Method | Path | Body → Response |
|---|---|---|
| POST | `/v1/batches/next` | `{size?: 5–10}` → `{batch_id, items: [{lexeme_id, es, en, reason, reason_kind, context}]}` |
| GET | `/v1/reviews/due` | → cards due now |
| POST | `/v1/reviews` | `{lexeme_id, rating: 1–4, reviewed_at?}` → `{due_at, scheduled_days, state, replayed?}`. `reviewed_at` replays an offline review (up to 14 days old); one older than the card's last review is ignored |
| POST | `/v1/pronunciation` | `{lexeme_id, expected, heard}` → `{score, ok, words: [{word, heard, ok, phonemes: [{p, ok, heard?}]}], tips}` |
| POST | `/v1/practice/compare` | `{expected, heard}` → same shape; used by the rescue drill and shadowing |

## Scenarios and rehearsal

| Method | Path | Body → Response |
|---|---|---|
| GET | `/v1/scenarios` | → `{upcoming, recurring, mine}` |
| POST | `/v1/scenarios` | `{title, details?, starts_at?, kind: "manual" \| "upcoming", share?: true, credit?: "anonymous" \| "name"}` → scenario with prep pack and `library: {status: "shared" \| "already_in_library" \| "private", template?: {id, title}, credit?, reason?}` |
| POST | `/v1/scenarios/calendar` | `{events: [{title, starts_at}]}` (titles read on device) → created/updated scenarios |
| GET | `/v1/scenarios/{id}` | → scenario + phrases + readiness |
| POST | `/v1/scenarios/{id}/readiness` | `{value: 1–5, phase}` → readiness |
| POST | `/v1/rehearsals` | `{scenario_id, difficulty}` → `{rehearsal_id, coach: {es, en}}` |
| POST | `/v1/rehearsals/{id}/turns` | `{text}` → `{native?, coach: {es, en}, done}` |
| POST | `/v1/rehearsals/{id}/end` | → `{summary, keep_phrases}` |

## Scene library

| Method | Path | Body → Response |
|---|---|---|
| GET | `/v1/library?q=&limit=` | → `{results: [{id, title, situation, topic, uses, credit, similarity}]}` in your variety; empty `q` lists the most used |
| GET | `/v1/library/{id}` | → scene card + phrases |
| POST | `/v1/library/{id}/use` | `{starts_at?, kind?}` → your new scenario with the pack (no generation) |
| POST | `/v1/library/{id}/report` | `{reason: "personal" \| "offensive" \| "wrong" \| "other"}` → `{ok: true}` |

## Progress

| Method | Path | Response |
|---|---|---|
| GET | `/v1/progress` | `{spanglish_ratio: [{week, ratio}], confidence: [{scenario, before, after}], words: {met, kept, due}, level_estimate: {level 0–5, band, basis, current_setting}, reflection: {sentences, spanish_share, words_kept, scenes_rehearsed, best_spanish, line}}` |
| GET | `/v1/notifications/plan?days=7&tz=Area/City` | `{timezone, budget, notifications: [{id, kind, fire_at, local, title, body, why, scenario_id}], suppressed: [{id, kind, reason}]}`; kinds `scene_soon`, `scene_eve`, `review`, `reflection` |
| GET | `/v1/lessons` | Lessons triggered by your sentences in the last 30 days: `{lessons: [{id, title, pattern, you_said}]}` |
| GET | `/v1/lessons/{id}` | `{id, title, pattern, rule, examples: [{en, es}], check: {prompt, options[3], answer}}` (options shuffled) |
| GET | `/v1/today` | `{next_scenario, words_ready, recent: [utterance]}` |
