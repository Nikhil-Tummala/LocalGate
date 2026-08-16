"""WebSocket telemetry hub: pushes a metrics snapshot to every connected dashboard each second."""
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.state import ProxyState

router = APIRouter()
INTERVAL_SECONDS = 1.0


def build_payload(state: ProxyState) -> dict:
    cfg = state.config
    snap = state.metrics.snapshot(state.limiter.min_tokens(), cfg.rate_limit.capacity)
    snap["target_url"] = cfg.target_url
    snap["cache_size"] = len(state.cache)
    return snap


async def broadcast(state: ProxyState) -> None:
    """Send one snapshot to all clients; drop any that fail."""
    if not state.websockets:
        return
    payload = build_payload(state)
    clients = list(state.websockets)
    results = await asyncio.gather(*(ws.send_json(payload) for ws in clients), return_exceptions=True)
    for ws, res in zip(clients, results):
        if isinstance(res, Exception):
            state.websockets.discard(ws)


async def broadcast_loop(state: ProxyState) -> None:
    while True:
        await asyncio.sleep(INTERVAL_SECONDS)
        await broadcast(state)


@router.websocket("/ws/telemetry")
async def telemetry(ws: WebSocket) -> None:
    state: ProxyState = ws.app.state.proxy
    await ws.accept()
    state.websockets.add(ws)
    try:
        await ws.send_json(build_payload(state))  # first frame immediately, don't wait for the tick
        while True:
            await ws.receive_text()  # we never expect input; this just notices disconnects
    except WebSocketDisconnect:
        pass
    finally:
        state.websockets.discard(ws)
