#!/usr/bin/env bash
# Sets up the 'langcoach' conda environment (first run) and starts the LangCoach backend, which also
# serves the web test build at http://localhost:<port>/web/.  macOS, Linux and WSL.
#
#   scripts/run-backend.sh                    # create env if needed, start on :8000
#   scripts/run-backend.sh --model local      # your OpenAI-compatible server (Hearth/Ollama) from backend/.env
#   scripts/run-backend.sh --model anthropic  # Claude (ANTHROPIC_API_KEY in backend/.env)
#   scripts/run-backend.sh --test             # run tests first
#   scripts/run-backend.sh --update           # reinstall/upgrade dependencies
#   scripts/run-backend.sh --host 0.0.0.0     # reachable from your iPhone on the same Wi-Fi
set -euo pipefail

ENV_NAME="langcoach"; PORT=8000; HOST="127.0.0.1"; MODEL=""; UPDATE=0; TEST=0; RELOAD=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --env) ENV_NAME="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --host) HOST="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --update) UPDATE=1; shift ;;
    --test) TEST=1; shift ;;
    --no-reload) RELOAD=0; shift ;;
    -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
step() { printf '\033[36m==> %s\033[0m\n' "$*"; }
note() { printf '    %s\n' "$*"; }

# 1. Find conda (works without `conda init`).
CONDA="${CONDA_EXE:-$(command -v conda || true)}"
if [[ -z "$CONDA" ]]; then
  for base in "$HOME/miniconda3" "$HOME/anaconda3" "$HOME/miniforge3" "$HOME/mambaforge" /opt/conda /opt/miniconda3; do
    [[ -x "$base/bin/conda" ]] && CONDA="$base/bin/conda" && break
  done
fi
[[ -n "$CONDA" ]] || { echo "Couldn't find conda. Install Miniconda/Miniforge first." >&2; exit 1; }
step "Using conda at $CONDA"

# 2. Create the environment on first run.
if ! "$CONDA" env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
  step "Creating conda env '$ENV_NAME' (Python 3.12) - first run only"
  "$CONDA" env create -n "$ENV_NAME" -f "$BACKEND/environment.yml"
  UPDATE=1
fi
PY="$("$CONDA" run -n "$ENV_NAME" python -c 'import sys; print(sys.executable)' | tail -n 1)"
[[ -x "$PY" ]] || { echo "Couldn't locate python in env '$ENV_NAME' (got '$PY')." >&2; exit 1; }
note "python: $PY"

# 3. Install dependencies (first run, --update, or if something's missing).
"$PY" -c "import fastapi, langgraph, deepagents, numpy, sqlalchemy, aiosqlite, cbor2" 2>/dev/null || UPDATE=1
if [[ "$UPDATE" == 1 ]]; then
  step "Installing backend dependencies"
  "$PY" -m pip install --upgrade pip --quiet
  "$PY" -m pip install -e "$BACKEND[dev]"
fi

# 4. Local settings.
if [[ ! -f "$BACKEND/.env" ]]; then
  cp "$BACKEND/.env.development" "$BACKEND/.env"
  step "Created backend/.env from .env.development"
  note "Edit backend/.env to point LLM_BASE_URL / LLM_FAST_MODEL at Hearth, then run with --model local."
fi
# Local testing clicks fast; production limits stay in config.py.
export RATE_LIMIT_PER_MINUTE="${RATE_LIMIT_PER_MINUTE:-600}" COACH_RATE_LIMIT_PER_MINUTE="${COACH_RATE_LIMIT_PER_MINUTE:-120}"
case "$MODEL" in
  fake) export LLM_PROVIDER=fake ;;
  local) export LLM_PROVIDER=openai_compatible ;;
  anthropic) export LLM_PROVIDER=anthropic ;;
  "") ;;
  *) echo "--model must be fake, local or anthropic" >&2; exit 2 ;;
esac
note "model provider: ${LLM_PROVIDER:-$(grep -E '^\s*LLM_PROVIDER\s*=' "$BACKEND/.env" | head -1 | cut -d= -f2 | tr -d ' ')}"

cd "$BACKEND"
# 5. Tests (optional).
if [[ "$TEST" == 1 ]]; then step "Running tests"; "$PY" -m pytest; fi

# 6. Start the server.
if command -v lsof >/dev/null && lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port $PORT is already in use (a model server, or another backend?). Try --port 8080." >&2; exit 1
fi
step "Starting backend on http://$HOST:$PORT"
note "web test build: http://localhost:$PORT/web/"
note "API docs:       http://localhost:$PORT/docs"
ARGS=(-m uvicorn app.main:app --host "$HOST" --port "$PORT")
[[ "$RELOAD" == 1 ]] && ARGS+=(--reload --reload-dir app)
exec "$PY" "${ARGS[@]}"
