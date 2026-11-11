# LangCoach

A Spanish confidence coach for iPhone. It listens to how *you* actually talk, says it back in
Spanish close to your own phrasing (and Spanish back to English, just as briefly), and prepares you
for the situations coming up in your life, not a fixed curriculum.

> Working name. The repo folder is `langcoach`; the product name is still open.

## Status

| Part | State |
|---|---|
| Plan, UX, design system | Done: see `docs/` and the clickable prototype |
| Backend (FastAPI + LangGraph) | Built; happy-path tests pass (`pytest`: 17) |
| iOS app (SwiftUI, iOS 26) | All screens written; **not yet compiled**: first build on a Mac will need a round of fixes |

Feature-by-feature status is in [`docs/02-feature-list.md`](docs/02-feature-list.md).

## What's here

| Path | What it is |
|---|---|
| `docs/` | Vision, feature list, UX, design system, architecture, security, data model, API, curation, roadmap |
| `design/` | OKLCH colour source + generator (asset catalog, Swift, CSS, contrast report) and the HTML prototype |
| `backend/` | API: Sign in with Apple, rotating sessions, App Attest, LangGraph graphs (coach, ingest, prep, rehearse), FSRS, curation |
| `ios/` | XcodeGen project, `LangCoachKit` Swift package (models, API client, offline queue), SwiftUI app |

## Run the backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
pytest                                                   # 17 happy-path tests, no model server needed
uvicorn app.main:app --reload --host 0.0.0.0             # http://localhost:8000/docs
```

**Models.** `LLM_PROVIDER=openai_compatible` points every LangGraph graph at any OpenAI-style endpoint
(Hearth, vLLM, llama.cpp, Ollama) via `LLM_BASE_URL` and `LLM_FAST_MODEL` / `LLM_SMART_MODEL`.
`anthropic` uses `ANTHROPIC_API_KEY`. `fake` is a tiny offline dictionary model for tests only.

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
