#!/usr/bin/env bash
#
# Runs the backend (FastAPI/uvicorn, via uv) and frontend (Next.js) dev
# servers together. Ctrl+C stops both.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

pids=()

cleanup() {
  echo
  echo "Stopping dev servers..."
  for pid in "${pids[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting backend (uvicorn --reload) on http://localhost:8000 ..."
(cd "$BACKEND_DIR" && uv run uvicorn app.main:app --reload) &
pids+=($!)

echo "Starting frontend (next dev --turbopack) on http://localhost:3000 ..."
(cd "$FRONTEND_DIR" && npm run dev) &
pids+=($!)

wait
