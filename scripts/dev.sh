#!/usr/bin/env bash
# One-shot local dev startup. Idempotent: safe to re-run.
# Brings up postgres, applies migrations, then runs api + web until you Ctrl-C.
#
# Note: venvs live outside iCloud Drive (~/.cache/inkling/{api,engine}-venv)
# and are symlinked into api/.venv and engine/.venv. iCloud's
# "Optimize Mac Storage" was offloading venv contents and breaking imports.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

API_PORT=8000
WEB_PORT=3000
VENV_HOME="$HOME/.cache/inkling"

log() { printf '\033[1;36m[dev]\033[0m %s\n' "$*"; }

ensure_venv() {
  local project=$1
  local target="$VENV_HOME/${project}-venv"
  local link="$project/.venv"
  if [ ! -e "$target/bin/python" ]; then
    log "creating $project venv at $target"
    mkdir -p "$VENV_HOME"
    rm -rf "$link" "$target"
    ( cd "$project" && UV_PROJECT_ENVIRONMENT="$target" uv sync )
  fi
  if [ ! -L "$link" ] || [ "$(readlink "$link")" != "$target" ]; then
    ln -snf "$target" "$link"
  fi
}

free_port() {
  local port=$1 name=$2 pids
  pids=$(lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null || true)
  if [ -n "$pids" ]; then
    log "killing stale $name on :$port ($pids)"
    kill $pids 2>/dev/null || true; sleep 1
    pids=$(lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null || true)
    [ -n "$pids" ] && kill -9 $pids 2>/dev/null || true
  fi
}

free_port "$API_PORT" api
free_port "$WEB_PORT" web

ensure_venv api
ensure_venv engine

if ! docker ps --format '{{.Names}}' | grep -q '^ink_postgres$'; then
  log "starting postgres"
  docker compose -f infra/docker-compose.yml up -d
fi
for _ in $(seq 1 30); do
  docker exec ink_postgres pg_isready -U inkling -q 2>/dev/null && break
  sleep 0.5
done

log "running alembic migrations"
( cd api && ./.venv/bin/alembic upgrade head )

PIDS=()
cleanup() {
  log "shutting down"
  for pid in "${PIDS[@]:-}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

log "starting api on :$API_PORT"
( cd api && ./.venv/bin/uvicorn app.main:app --reload --reload-dir app --port "$API_PORT" ) &
PIDS+=($!)

log "starting web on :$WEB_PORT"
( cd web && ./node_modules/.bin/next dev -p "$WEB_PORT" ) &
PIDS+=($!)

log "ready — api http://localhost:$API_PORT  web http://localhost:$WEB_PORT  (Ctrl-C to stop)"
wait
