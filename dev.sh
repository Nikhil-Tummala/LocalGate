#!/usr/bin/env bash
# Run backend (:8000) and dashboard (:5173) together. Usage: ./dev.sh [target-url]
set -e
cd "$(dirname "$0")"
[ -d backend/.venv ] || { python3 -m venv backend/.venv && backend/.venv/bin/pip install -q -r backend/requirements.txt; }
[ -d frontend/node_modules ] || (cd frontend && npm install)
trap 'kill 0' EXIT
(cd backend && LOCALGATE_TARGET_URL="$1" .venv/bin/uvicorn app.main:app --port 8000) &
(cd frontend && npm run dev -- --host 127.0.0.1) &
wait
