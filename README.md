# LocalGate

A local API gateway for developers. An async reverse proxy (FastAPI + httpx) with a
token-bucket rate limiter, an LRU response cache and a chaos injector, plus a live
React dashboard to watch traffic and change settings without restarting.

## Quick start

Needs Python 3.11+ and Node 22 (Vite 8 needs 20.19+ or 22.12+). Developed on Python 3.13 / Node 22.

```bash
# backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
LOCALGATE_TARGET_URL=http://localhost:3000 .venv/bin/uvicorn app.main:app --port 8000

# frontend (second terminal)
cd frontend && npm install && npm run dev      # http://127.0.0.1:5173
```

Or run both with `./dev.sh http://localhost:3000`. It switches to Node 22 via nvm (`frontend/.nvmrc`)
and uses ports 8000 (gateway) and 5173 (dashboard); override with `GATEWAY_PORT` / `DASHBOARD_PORT`.

Point your client at `http://localhost:8000` instead of the real API. The target can also
be set per request with an `X-Target-URL` header, or live from the dashboard.

## Dashboard

Connection bar (live status, editable target), KPI cards (RPS, cache hit ratio, bucket
tokens, p95 latency), a 60 s cache-hit vs upstream chart, chaos sliders and toggles, a
cache flush button and rate-limit capacity/refill inputs. Applying new rate limits resets
every bucket to full.

## Request pipeline

1. Parse request metadata (target, path, query, body)
2. **Rate limiter**, token bucket per path. Empty bucket gives `429` with `Retry-After`
3. **Chaos injector**, optional random delay, then optional synthetic 5xx (upstream untouched)
4. **Cache**, `GET` only. Hit returns immediately with `X-Proxy-Cache: HIT`
5. Forward upstream, streaming the body (`httpx` `build_request` + `send(stream=True)`)
6. Store `200` GET responses in the cache (`X-Proxy-Cache: MISS`)
7. Return to the client

Every response from steps 2 onward carries `X-RateLimit-Limit`, `X-RateLimit-Remaining`
and `X-RateLimit-Reset`.

## Control API

| Endpoint | Purpose |
|---|---|
| `GET /api/config` | Current configuration |
| `POST /api/config` | Partial, validated, live update. Send only what changes |
| `POST /api/cache/clear` | Flush the cache, returns `{"cleared": n}` |
| `WS /ws/telemetry` | Metrics snapshot on connect, then every second |

```bash
curl -X POST localhost:8000/api/config -H 'content-type: application/json' \
  -d '{"chaos": {"error_injection_enabled": true, "failure_rate_percentage": 0.25}}'
```

`failure_rate_percentage` is a fraction from 0.0 to 1.0. Invalid updates return `422` and
change nothing.

## Known limits

- State is in memory: a restart clears the cache, buckets and metrics.
- Request bodies are buffered. Response bodies stream; those over `cache.max_body_bytes`
  (1 MiB) are streamed but not cached.
- The cache key ignores request headers, so authenticated GETs to the same URL share an
  entry. Fine for local development, not for multi-user traffic.
- Single process, single event loop (metrics need no locks). Don't run with `--workers > 1`.

## Tests

```bash
cd backend && .venv/bin/pytest
```
