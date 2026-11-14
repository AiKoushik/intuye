# Security model

Goal: every request proves **who** (user session) and **what** (the genuine Intuye app on a real
device), carries the minimum data, and can only touch that user's rows. Audit target: OWASP MASVS v2
(2023) for the app and the OWASP API Security Top 10 (2023) for the server.

## Threat model (summary)

| Threat | Example | Control |
|---|---|---|
| Account takeover | Stolen refresh token | Rotating refresh tokens with reuse detection; Keychain `afterFirstUnlockThisDeviceOnly` |
| API abuse / scraping | Script calls `/v1/coach` with a stolen token to get free LLM calls | App Attest assertion required on every call; per-user and per-IP rate limits |
| Broken object-level authorization (API1:2023) | `GET /v1/scenarios/{id}` for another user's id | Every query scoped by `user_id` in the repository layer; ids are random UUIDs; tests cover cross-user access |
| Prompt injection from ambient audio | A TV in the background says "ignore your instructions" | Transcripts passed as delimited data; models have no tools; outputs schema-validated and length-limited |
| Replay | Captured request re-sent | Assertion counter must strictly increase; client data includes method, path, body hash, timestamp (±5 min) |
| Data exposure | Logs leaking transcripts | No request bodies in logs; request IDs only; transcripts encrypted at rest by the database volume |
| Privacy overreach | Audio uploaded | Architecture: audio never leaves the phone; only text is sent |

## Step by step

### 1. Sign up / sign in (Sign in with Apple)

```
App                                   Server                              Apple
 │ nonce = random 32 bytes             │                                    │
 │ ASAuthorizationAppleIDRequest       │                                    │
 │   .nonce = SHA256(nonce) ─────────────────────────────────────────────────►
 │ ◄──────────── identityToken (JWT), authorizationCode ─────────────────────│
 │ POST /v1/auth/apple {identity_token, raw_nonce} (+ App Attest assertion)  │
 │ ───────────────────────────────────►│ fetch JWKS (cached 24 h) ─────────►│
 │                                     │ verify: signature (RS256, kid),    │
 │                                     │ iss = https://appleid.apple.com,   │
 │                                     │ aud = bundle id, exp, nonce =      │
 │                                     │ SHA256(raw_nonce)                  │
 │                                     │ upsert user by `sub`               │
 │ ◄──── {access_token, refresh_token, expires_in} ─────│                    │
```

Apple's guideline 4.8 is satisfied because Sign in with Apple is offered (and is the only option in
v1). Passkeys arrive in P3.

### 2. Session tokens

| Token | Format | Lifetime | Storage |
|---|---|---|---|
| Access | JWT, Ed25519 (`EdDSA`), claims `sub`, `sid`, `iat`, `exp`, `aud`, `iss`, `jti` | 10 min | Memory only |
| Refresh | Opaque 256-bit random; server stores SHA-256 hash | 14 days idle, 60 days absolute | Keychain, this device only |

**Rotation with reuse detection** (RFC 9700, OAuth 2.0 Security Best Current Practice, Jan 2025):
every refresh consumes the old token and issues a new one in the same *family*. Presenting an
already-consumed token revokes the whole family and forces sign-in.

### 3. App Attest (every API call)

**Registration (once per install):**
1. `GET /v1/attest/challenge` → single-use 32-byte challenge (5-min TTL).
2. App: `generateKey()` → `attestKey(keyId, clientDataHash: SHA256(challenge))`.
3. `POST /v1/attest/register` → server verifies, per Apple's documented procedure:
   x5c chain to the Apple App Attestation Root CA; nonce extension (OID `1.2.840.113635.100.8.2`)
   equals `SHA256(authData ‖ SHA256(challenge))`; `SHA256(credential public key) == keyId`;
   `rpIdHash == SHA256(TeamID.bundleID)`; counter = 0; AAGUID is `appattestdevelop` or
   `appattest` (production); credential id = keyId. Stores the public key and counter.

**Every request:** the app sends `X-LC-Key-Id` and `X-LC-Assertion` (CBOR `{signature,
authenticatorData}`) over client data `METHOD\nPATH\nSHA256(body)\nTIMESTAMP` (timestamp also in
`X-LC-Timestamp`). The server rebuilds client data, checks the timestamp is within ±5 min,
verifies the ECDSA P-256 signature over `SHA256(authenticatorData ‖ SHA256(clientData))`, checks
`rpIdHash`, and requires the counter to strictly increase.

**Modes:** `APP_ATTEST_MODE=enforce | report | off`. `off` exists only because the Simulator cannot
attest; the server refuses to start with `off` when `ENV=production`.

### 4. Authorisation on every object

All data access goes through functions that take `user_id` and filter by it. There is no endpoint
that accepts a `user_id` parameter. Resource ids are UUIDv4.

### 5. Limits

| Limit | Value |
|---|---|
| Request body | 64 KB (utterance batches 256 KB) |
| Coach input | 1,000 characters |
| Utterances per batch | 200 |
| Rate limits | 60 req/min/user general; 20/min coach; 10/min auth per IP |

### 6. Transport and headers

TLS 1.2+ (1.3 preferred) with HSTS; responses carry `Cache-Control: no-store`,
`X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, and a request id. The app uses
App Transport Security defaults; certificate pinning via `NSPinnedDomains` is a P3 option.

### 7. Data lifecycle

- **Account deletion** (App Store guideline 5.1.1(v)): `DELETE /v1/account` removes every user row
  and revokes all sessions; the app also deletes Keychain items and local caches.
- **Export:** `GET /v1/account/export` returns all user data as JSON.
- **Forget recent:** `POST /v1/utterances/forget {minutes}` deletes the last N minutes of moments.
- **Retention:** moments auto-delete after the user's chosen window (default 90 days); learning state
  (cards, reviews) stays until account deletion.

### 8. LLM safety

- System prompts state that user text is data, never instructions; user text is wrapped in
  `<user_text>` tags.
- Agents get only our own tools: the scene builder's read-only `search_scene_library`, scoped to
  published, generalised scenes. Deep Agents' filesystem and shell tools are disabled. No agent can
  read another learner's private data.
- Library text written by other learners is wrapped as data whenever it reaches an agent.
- Outputs must validate against Pydantic schemas; invalid output → one retry → safe fallback.
- Model API keys exist only on the server.

### 9. Shared scene library

- **What is shared:** the scene builder's generalised card (title, one-sentence situation, topic),
  the Spanish variety, the level and the phrase pack. The phrase writer is told never to put names,
  places, employers, dates or numbers in phrases.
- **Never shared:** your own title, details, dates, readiness ratings, rehearsals and anything from
  Calendar. Calendar scenes are never published.
- **Anonymous by default:** an anonymous share stores no link to you at all. With *Show my name*, the
  scene keeps your user id and display name; deleting your account removes both and the scene stays
  anonymous.
- **Gates before publishing:** the learner chose to share; the builder marked it `shareable`; a
  pattern check finds no email, phone number, URL or long digit run; nothing the same or similar is
  already published in that variety.
- **Reports:** `POST /v1/library/{id}/report`, one per learner per scene; three reports hide the
  scene from search until reviewed (App Store guideline 1.2 requires reporting for user-generated
  content).

## MASVS v2 mapping (app)

| Control group | How |
|---|---|
| STORAGE | Tokens in Keychain (`ThisDeviceOnly`); no secrets in `UserDefaults`; capture buffer in memory |
| CRYPTO | Platform crypto only (CryptoKit, Secure Enclave via App Attest) |
| AUTH | SIWA + server-side sessions; biometric lock optional (P3) |
| NETWORK | ATS, TLS 1.2+, optional pinning |
| PLATFORM | Microphone and calendar permission requested in context with purpose strings |
| CODE | No third-party SDKs in v1; dependency review for any added later |
| RESILIENCE | App Attest |
| PRIVACY | On-device transcription, privacy nutrition label, data export and deletion |
