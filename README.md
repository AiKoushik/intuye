# LangCoach

A Spanish confidence coach for iPhone. It listens to how *you* actually talk, says it back in
Spanish close to your own phrasing (and Spanish back to English, just as briefly), and prepares you
for the situations coming up in your life, not a fixed curriculum.

> Working name. The repo folder is `langcoach`; the product name is still open.

## Status

| Part | State |
|---|---|
| Plan, UX, design system | Done: see `docs/` and the clickable prototype |
| Backend (FastAPI + LangChain Deep Agents) | Built; happy-path tests pass (`pytest`) |
| iOS app (SwiftUI, iOS 26) | All screens written; **not yet compiled**: first build on a Mac will need a round of fixes |

Feature-by-feature status is in [`docs/02-feature-list.md`](docs/02-feature-list.md).

## What's here

| Path | What it is |
|---|---|
| `docs/` | Vision, feature list, UX, design system, architecture, security, data model, API, curation, roadmap |
| `design/` | OKLCH colour source + generator (asset catalog, Swift, CSS, contrast report) and the HTML prototype |
| `backend/` | API: Sign in with Apple, rotating sessions, App Attest, Deep Agents (translator, explainer, ingest analyst, scene builder + phrase writer, rehearsal partner, summariser), shared scene library, FSRS, curation |
| `ios/` | XcodeGen project, `LangCoachKit` Swift package (models, API client, offline queue), SwiftUI app |

## Run it (conda)

One command sets up the `langcoach` conda env on first run, installs dependencies, creates
`backend/.env` from `backend/.env.development`, starts the API, and opens the **web test build**:

```powershell
# Windows (PowerShell, or double-click scripts\run-backend.bat)
.\scripts\run-backend.ps1                    # http://localhost:8000/web/  (API docs at /docs)
.\scripts\run-backend.ps1 -Model local       # use Hearth / Ollama / vLLM from backend\.env
.\scripts\run-backend.ps1 -Model anthropic   # use Claude (ANTHROPIC_API_KEY in backend\.env)
.\scripts\run-backend.ps1 -Test              # run the tests first
.\scripts\run-backend.ps1 -Update            # reinstall dependencies
.\scripts\run-backend.ps1 -BindHost 0.0.0.0  # reachable from your iPhone on the same Wi-Fi
```

```bash
# macOS / Linux / WSL
scripts/run-backend.sh [--model local|anthropic|fake] [--test] [--update] [--host 0.0.0.0] [--port 8000]
```

Out of the box `LLM_PROVIDER=fake` (a tiny offline dictionary) so you can click through every screen
without a model server. For real Spanish, set `LLM_BASE_URL`, `LLM_FAST_MODEL` and `LLM_SMART_MODEL`
in `backend/.env` to your Hearth endpoint and run with `-Model local`.

### The web test build

`web/` mirrors the iPhone screens (same colour tokens, layout and flows) against the real API, served by
the backend at `/web` in development. Sign-in is a dev-only name field (`DEV_LOGIN_ENABLED`), App Attest
is off locally, speech uses the browser (Chrome or Edge), and the Capture sheet has a
"pretend capture heard these" box for testing curation without a mic.

Everything the backend does can be tried from it: Say (both directions and questions), capture and
Moments (sentences by hour, delete, forget the last 10 minutes), word batches and review with spoken
answers, scenes (build, library search by text or voice, use, share, report, rehearse, archive),
Progress, and Settings (variety, level, notifications, quiet hours, retention, export, delete). The
side panel has a short "Try this" list. Open a private window and sign in with another name to see
shared library scenes from a second learner's side.

### Manual setup (without the scripts)

```bash
conda env create -f backend/environment.yml && conda activate langcoach
cd backend && pip install -e ".[dev]" && cp .env.development .env
pytest                                                   # happy-path tests, no model server needed
uvicorn app.main:app --reload                            # http://localhost:8000/web/
```

**Models.** `LLM_PROVIDER=openai_compatible` points every Deep Agent at any OpenAI-style endpoint
(Hearth, vLLM, llama.cpp, Ollama) via `LLM_BASE_URL` and `LLM_FAST_MODEL` / `LLM_SMART_MODEL`. The
model must support tool calling, because agents use tools for structured output and subagents.
`anthropic` uses `ANTHROPIC_API_KEY`. `fake` is a tiny offline tool-calling model for tests only.
Python 3.11+ is required (Deep Agents).

**Database.** SQLite by default for development; set `DATABASE_URL` to Postgres
(`postgresql+asyncpg://…`) for real use.

## Build the iPhone app (Mac with Xcode 26+)

```bash
brew install xcodegen
cd ios && xcodegen generate && open LangCoach.xcodeproj
```

1. Set your Team ID in `ios/project.yml` (`DEVELOPMENT_TEAM`) and a real bundle id (also set
   `APPLE_BUNDLE_ID` / `APPLE_TEAM_ID` in the backend `.env` to match).
2. In the Apple Developer portal, enable **Sign in with Apple** and **App Attest** for the App ID.
3. **Simulator:** App Attest isn't available, so run the backend with `APP_ATTEST_MODE=report` (or `off`).
   **Device:** set `LC_API_BASE_URL` (Debug) in `project.yml` to your machine's LAN address, e.g.
   `http://192.168.1.20:8000`, and keep `APP_ATTEST_MODE=report` until the first registration succeeds,
   then switch to `enforce`.

## Regenerate design tokens

```bash
python design/tokens/generate.py --check   # rebuilds Swift, CSS, JSON, asset catalog; fails on any contrast miss
```

Open `design/prototype/index.html` in a browser for the clickable screens.
