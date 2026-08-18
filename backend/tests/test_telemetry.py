from app.api import telemetry
from app.main import app


def test_first_frame_is_sent_on_connect_and_reflects_traffic(client):
    client.get("/a")
    client.get("/a")
    with client.websocket_connect("/ws/telemetry") as ws:
        snap = ws.receive_json()
    assert snap["total_requests"] == 2 and snap["cache_hits"] == 1 and snap["cache_hit_ratio"] == 50.0
    assert snap["target_url"] == "http://upstream.test" and snap["bucket_capacity"] == 60
    assert len(snap["series"]) == 60 and snap["tokens"] <= 60
    assert {"rps", "p50_ms", "p95_ms", "rate_limited", "cache_size"} <= snap.keys()


def test_broadcast_reaches_all_clients_and_disconnects_are_dropped(client):
    state = app.state.proxy
    with client.websocket_connect("/ws/telemetry") as a, client.websocket_connect("/ws/telemetry") as b:
        a.receive_json(), b.receive_json()
        assert len(state.websockets) == 2
        client.get("/x")
        client.portal.call(telemetry.broadcast, state)
        assert a.receive_json()["total_requests"] == 1 and b.receive_json()["total_requests"] == 1
    assert len(state.websockets) == 0


def test_lifespan_loop_pushes_frames_without_being_asked(client, monkeypatch):
    monkeypatch.setattr(telemetry, "INTERVAL_SECONDS", 0.05)  # the loop re-reads this each tick
    with client.websocket_connect("/ws/telemetry") as ws:
        ws.receive_json()  # on-connect frame
        client.get("/tick")
        assert ws.receive_json()["total_requests"] >= 0  # blocks until the loop sends a frame
        assert ws.receive_json()["total_requests"] == 1
