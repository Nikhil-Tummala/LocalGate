"""LocalGate entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import proxy
from app.core.config import AppConfig
from app.core.state import ProxyState


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.proxy = ProxyState.create(AppConfig.from_env())
    yield
    await app.state.proxy.client.aclose()


app = FastAPI(title="LocalGate", lifespan=lifespan)
# control routes (/api/*, /ws/*) must be included above this line: the proxy route matches every path
app.include_router(proxy.router)
