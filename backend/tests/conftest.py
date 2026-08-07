import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import AppConfig
from app.main import app


class Upstream:
    """Fake upstream API: records calls, replies from a settable function."""

    def __init__(self):
        self.calls: list[httpx.Request] = []
        self.reply = lambda req: httpx.Response(200, json={"ok": True}, headers={"content-type": "application/json"})

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        return self.reply(request)


@pytest.fixture
def upstream():
    return Upstream()


@pytest.fixture
def client(upstream):
    with TestClient(app) as c:
        state = app.state.proxy
        state.client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
        state.apply(AppConfig(target_url="http://upstream.test"))
        yield c
