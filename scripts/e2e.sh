#!/usr/bin/env bash
# Runs the web end-to-end test against a fresh backend (fake model, throwaway database).
# usage  scripts/e2e.sh [screenshot-dir]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8766}"
DB="$(mktemp -d)/e2e.db"
cd "$ROOT/backend"
ENV=development DATABASE_URL="sqlite+aiosqlite:///$DB" APP_ATTEST_MODE=off DEV_LOGIN_ENABLED=true LLM_PROVIDER=fake \
  EMBED_PROVIDER=hash RATE_LIMIT_PER_MINUTE=600 COACH_RATE_LIMIT_PER_MINUTE=120 \
  python -m uvicorn app.main:app --port "$PORT" > "$(dirname "$DB")/server.log" 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true' EXIT
for _ in $(seq 1 200); do curl -sf "http://localhost:$PORT/health" >/dev/null && break; sleep 0.3; done
cd "$ROOT/web/e2e"
[ -n "${1:-}" ] && mkdir -p "$1"
BASE_URL="http://localhost:$PORT" node flow.js "${1:-}"
