from app.main import app


def test_partial_update_merges_nested_fields(client):
    r = client.post("/api/config", json={"chaos": {"latency_enabled": True, "max_delay_ms": 900}})
    assert r.status_code == 200
    chaos = client.get("/api/config").json()["chaos"]
    assert chaos["latency_enabled"] is True and chaos["max_delay_ms"] == 900
    assert chaos["min_delay_ms"] == 100  # untouched
    assert app.state.proxy.config.chaos.latency_enabled  # live in the running services
    assert app.state.proxy.chaos.cfg.latency_enabled


def test_target_and_rate_limit_apply_without_restart(client, upstream):
    client.post("/api/config", json={"target_url": "http://new.test/", "rate_limit": {"capacity": 1, "refill_rate": 0.001}})
    assert client.get("/a").status_code == 200 and str(upstream.calls[0].url) == "http://new.test/a"
    assert client.get("/b").status_code == 200  # separate route, own bucket
    assert client.get("/a?x=1").status_code == 429  # buckets are per path; the query string is ignored


def test_invalid_updates_are_rejected_and_state_is_unchanged(client):
    before = client.get("/api/config").json()
    for bad in [{"chaos": {"min_delay_ms": 500, "max_delay_ms": 1}}, {"chaos": {"failure_rate_percentage": 7}},
                {"target_url": "ftp://x"}, {"typo": 1}]:
        assert client.post("/api/config", json=bad).status_code == 422
    assert client.get("/api/config").json() == before


def test_cache_clear_flushes_everything(client, upstream):
    client.get("/a")
    client.get("/b")
    assert client.post("/api/cache/clear").json() == {"cleared": 2}
    assert client.get("/a").headers["x-proxy-cache"] == "MISS"


def test_control_routes_win_over_catch_all(client, upstream):
    client.get("/api/config")
    assert not upstream.calls
