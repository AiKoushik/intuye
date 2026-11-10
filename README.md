# LangCoach

A Spanish confidence coach for iPhone. It listens to how *you* actually talk, says it back in
Spanish close to your own phrasing, and prepares you for the situations coming up in your life —
not a fixed curriculum.

> Working name. The repo folder is `langcoach`; the product name is still open.

## What's here

| Path | What it is |
|---|---|
| `docs/` | Product vision, feature list, UX, design system, architecture, security, API, roadmap |
| `design/` | Colour-token source (OKLCH), generator, generated tokens, clickable HTML prototype |
| `backend/` | Python 3.11+ / FastAPI / Postgres API: auth, App Attest, translation, curation, FSRS |
| `ios/` | SwiftUI app (iOS 26+) generated with XcodeGen, plus the `LangCoachKit` Swift package |

Start with [`docs/01-product-vision.md`](docs/01-product-vision.md) and
[`docs/02-feature-list.md`](docs/02-feature-list.md).

## Quick start

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env                                  # fill in secrets
uvicorn app.main:app --reload
pytest
```

### iOS (needs a Mac with Xcode 26+)

```bash
brew install xcodegen
cd ios && xcodegen generate && open LangCoach.xcodeproj
```

### Design tokens

```bash
python design/tokens/generate.py     # rebuilds Swift, CSS, JSON and the asset catalog
open design/prototype/index.html     # clickable screen prototype
```
