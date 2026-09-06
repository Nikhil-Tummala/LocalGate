"""Real sockets end to end: uvicorn + a stdlib upstream. MockTransport can't prove streaming."""
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest
import uvicorn

from app.main import app


class Upstream(BaseHTTPRequestHandler):
    hits = 0

    def do_GET(self):
        if self.path == "/stream":
            self.send_response(200)
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            for i in range(3):
                b = f"chunk{i}".encode()
                self.wfile.write(f"{len(b):x}\r\n".encode() + b + b"\r\n")
                self.wfile.flush()
                time.sleep(0.3)
            self.wfile.write(b"0\r\n\r\n")
            return
        Upstream.hits += 1
        body = b'{"n": %d}' % Upstream.hits
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def gateway(monkeypatch):
    up = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    threading.Thread(target=up.serve_forever, daemon=True).start()
    Upstream.hits = 0
    monkeypatch.setenv("LOCALGATE_TARGET_URL", f"http://127.0.0.1:{up.server_address[1]}")
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    while not server.started:
        time.sleep(0.02)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    t.join(5)
    up.shutdown()


def test_response_is_streamed_not_buffered(gateway):
    arrivals = []
    start = time.perf_counter()
    with httpx.Client(trust_env=False, timeout=10) as c, c.stream("GET", gateway + "/stream") as r:
        assert r.status_code == 200
        for chunk in r.iter_raw():
            arrivals.append((time.perf_counter() - start, chunk))
    assert b"".join(c for _, c in arrivals) == b"chunk0chunk1chunk2"
    # first byte long before the upstream finishes (~0.9s): proves we relay as we receive
    assert arrivals[0][0] < 0.6 and arrivals[-1][0] > 0.6


def test_cache_over_real_sockets(gateway):
    with httpx.Client(trust_env=False) as c:
        a, b = c.get(gateway + "/item?y=2&x=1"), c.get(gateway + "/item?x=1&y=2")
    assert (a.headers["x-proxy-cache"], b.headers["x-proxy-cache"]) == ("MISS", "HIT")
    assert a.json() == b.json() == {"n": 1} and Upstream.hits == 1
