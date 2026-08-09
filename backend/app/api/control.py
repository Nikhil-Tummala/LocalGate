"""Control API: live config updates and cache flush."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from app.core.config import AppConfig
from app.core.state import ProxyState

router = APIRouter(prefix="/api")


def _merge(base: dict, patch: dict) -> dict:
    """Recursive dict merge, so {"chaos": {"latency_enabled": true}} only touches that one field."""
    out = dict(base)
    for k, v in patch.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


@router.get("/config")
async def get_config(request: Request) -> dict:
    return request.app.state.proxy.config.model_dump()


@router.post("/config")
async def update_config(request: Request, patch: dict) -> dict:
    state: ProxyState = request.app.state.proxy
    try:
        new = AppConfig.model_validate(_merge(state.config.model_dump(), patch))
    except ValidationError as e:
        raise HTTPException(422, detail=e.errors(include_url=False, include_context=False))
    state.apply(new)
    return new.model_dump()


@router.post("/cache/clear")
async def clear_cache(request: Request) -> dict:
    return {"cleared": request.app.state.proxy.cache.clear()}
