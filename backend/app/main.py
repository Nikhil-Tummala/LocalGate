"""LocalGate entry point."""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import control, proxy, telemetry
from app.core.config import AppConfig
from app.core.state import ProxyState


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = app.state.proxy = ProxyState.create(AppConfig.from_env())
    task = asyncio.create_task(telemetry.broadcast_loop(state))
    yield
    task.cancel()
    await state.client.aclose()


app = FastAPI(title="LocalGate", lifespan=lifespan)
# control routes (/api/*, /ws/*) must be included above this line: the proxy route matches every path
app.include_router(control.router)
app.include_router(telemetry.router)
app.include_router(proxy.router)
