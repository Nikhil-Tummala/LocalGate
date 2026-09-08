"""Catch-all reverse proxy. Pipeline: parse -> rate limit -> chaos -> cache -> upstream -> store -> respond."""
import time

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from app.core.state import ProxyState
from app.services import forwarder
from app.services.cache import make_key
from app.services.chaos import error_payload

router = APIRouter()
METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH"]


def _ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000


def _json(status: int, payload: dict, headers: dict[str, str]) -> JSONResponse:
    return JSONResponse(payload, status_code=status, headers=headers)


async def _stream_and_cache(upstream: httpx.Response, state: ProxyState, started: float, cache_key: str | None):
    """Relay the upstream body chunk by chunk; keep a copy only while it fits in the cache limit."""
    cfg = state.config.cache
    chunks: list[bytes] | None = [] if cache_key else None
    size = 0
    try:
        async for chunk in upstream.aiter_bytes():
            if chunks is not None:
                size += len(chunk)
                if size > cfg.max_body_bytes:
                    chunks = None  # too big to cache: stop buffering, keep streaming
                else:
                    chunks.append(chunk)
            yield chunk
        if chunks is not None:  # only reached when the client received the whole body
            state.cache.put(
                cache_key, b"".join(chunks), upstream.status_code,
                upstream.headers.get("content-type"), cfg.ttl_seconds,
            )
    finally:
        await upstream.aclose()
        state.metrics.record(_ms(started), cache="MISS" if cache_key else None)


@router.api_route("/{path:path}", methods=METHODS)
async def proxy(request: Request, path: str) -> Response:
    started = time.perf_counter()
    state: ProxyState = request.app.state.proxy
    raw_path = request.scope.get("raw_path", request.url.path.encode()).decode("latin-1")

    # 1. parse request metadata
    base = (request.headers.get("x-target-url") or state.config.target_url or "").strip().rstrip("/")
    if not base.startswith(("http://", "https://")):
        return _json(400, {"error": "no_target", "message": "Set a target via POST /api/config or the X-Target-URL header"}, {})
    url = base + raw_path + (f"?{request.url.query}" if request.url.query else "")
    body = await request.body()  # ponytail: request bodies are buffered; upload streaming isn't needed locally

    # 2. rate limit
    # one bucket per path; idle ones are pruned by the limiter once there are too many routes
    decision = await state.limiter.acquire(raw_path)
    rl_headers = decision.headers()
    if not decision.allowed:
        state.metrics.record(_ms(started), outcome="limited")
        return _json(429, {"error": "rate_limited", "retry_after": decision.retry_after},
                     {**rl_headers, "Retry-After": str(decision.retry_after)})

    # 3. chaos
    chaos = await state.chaos.apply()
    if chaos.error_status:
        state.metrics.record(_ms(started), outcome="synthetic")
        return _json(chaos.error_status, error_payload(chaos.error_status), rl_headers)

    # 4. cache lookup (GET only)
    cache_key = make_key("GET", url) if request.method == "GET" else None
    if cache_key:
        hit = state.cache.get(cache_key)
        if hit:
            state.metrics.record(_ms(started), cache="HIT")
            headers = {**rl_headers, "X-Proxy-Cache": "HIT"}
            if hit.content_type:
                headers["content-type"] = hit.content_type
            return Response(hit.body, status_code=hit.status_code, headers=headers)

    # 5. forward upstream
    try:
        upstream = await forwarder.open_upstream(
            state.client, request.method, url, forwarder.clean_request_headers(request.headers), body
        )
    except httpx.TimeoutException:
        state.metrics.record(_ms(started))
        return _json(504, {"error": "upstream_timeout"}, rl_headers)
    except httpx.HTTPError as e:
        state.metrics.record(_ms(started))
        return _json(502, {"error": "upstream_unreachable", "message": type(e).__name__}, rl_headers)

    # 6. store in cache (200 GETs that fit) while 7. streaming to the client
    cacheable = cache_key if upstream.status_code == 200 and _fits(upstream, state) else None
    response = StreamingResponse(_stream_and_cache(upstream, state, started, cacheable), status_code=upstream.status_code)
    for k, v in forwarder.clean_response_headers(upstream.headers):
        response.raw_headers.append((k.lower().encode("latin-1"), v.encode("latin-1")))
    for k, v in rl_headers.items():
        response.headers[k] = v
    if cache_key:
        response.headers["X-Proxy-Cache"] = "MISS"
    return response


def _fits(upstream: httpx.Response, state: ProxyState) -> bool:
    declared = upstream.headers.get("content-length")
    return not (declared and declared.isdigit() and int(declared) > state.config.cache.max_body_bytes)
