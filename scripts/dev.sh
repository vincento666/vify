#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${HIFY_HOST:-127.0.0.1}"
BACKEND_PORT="${HIFY_BACKEND_PORT:-8000}"
FRONTEND_PORT="${HIFY_FRONTEND_PORT:-5173}"
BACKEND_URL="http://${HOST}:${BACKEND_PORT}"

if [[ "${1:-}" == "--help" ]]; then
  printf 'Usage: HIFY_BACKEND_PORT=8000 HIFY_FRONTEND_PORT=5173 scripts/dev.sh\n'
  exit 0
fi

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then kill "${BACKEND_PID}" 2>/dev/null || true; fi
  if [[ -n "${FRONTEND_PID:-}" ]]; then kill "${FRONTEND_PID}" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM

cd "${ROOT_DIR}"
uv run uvicorn app.main:app --host "${HOST}" --port "${BACKEND_PORT}" &
BACKEND_PID=$!

cd "${ROOT_DIR}/frontend"
VITE_BACKEND_URL="${BACKEND_URL}" npm run dev -- --host "${HOST}" --port "${FRONTEND_PORT}" --strictPort &
FRONTEND_PID=$!

printf 'Backend:  %s\n' "${BACKEND_URL}"
printf 'Frontend: http://%s:%s\n' "${HOST}" "${FRONTEND_PORT}"

wait "${BACKEND_PID}" "${FRONTEND_PID}"
