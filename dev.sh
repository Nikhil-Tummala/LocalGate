#!/usr/bin/env bash
# Run backend and dashboard together. Usage: ./dev.sh [target-url]
# Ports: GATEWAY_PORT (default 8000), DASHBOARD_PORT (default 5173)
set -e
cd "$(dirname "$0")"
export GATEWAY_PORT="${GATEWAY_PORT:-8000}" DASHBOARD_PORT="${DASHBOARD_PORT:-5173}"
# Vite 8 needs Node 20.19+/22.12+; switch with nvm if the shell defaults to something older
[ -s "$HOME/.nvm/nvm.sh" ] && . "$HOME/.nvm/nvm.sh" && nvm use "$(cat frontend/.nvmrc)" >/dev/null
node -e 'process.exit(+process.versions.node.split(".")[0] >= 20 ? 0 : 1)' || { echo "Node 20+ required (found $(node -v)). Install Node 22." >&2; exit 1; }
[ -d backend/.venv ] || { python3 -m venv backend/.venv && backend/.venv/bin/pip install -q -r backend/requirements.txt; }
[ -d frontend/node_modules ] || (cd frontend && npm install)
trap 'kill 0' EXIT
(cd backend && LOCALGATE_TARGET_URL="$1" .venv/bin/uvicorn app.main:app --port "$GATEWAY_PORT") &
(cd frontend && npm run dev -- --host 127.0.0.1 --port "$DASHBOARD_PORT" --strictPort) &
wait
