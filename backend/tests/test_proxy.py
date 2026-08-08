import httpx

from app.core.config import AppConfig, CacheConfig, ChaosConfig, RateLimitConfig
from app.main import app


def configure(**kw):
    app.state.proxy.apply(AppConfig(target_url="http://upstream.test", **kw))


def test_forwards_method_path_query_and_body(client, upstream):
    r = client.post("/v1/items?a=1", content=b"payload", headers={"x-custom": "yes"})
    assert r.status_code == 200 and r.json() == {"ok": True}
    req = upstream.calls[0]
    assert (req.method, str(req.url), req.content) == ("POST", "http://upstream.test/v1/items?a=1", b"payload")
    assert req.headers["x-custom"] == "yes" and req.headers["host"] == "upstream.test"


def test_x_target_url_header_overrides_config(client, upstream):
    client.get("/p", headers={"X-Target-URL": "http://other.test"})
    assert str(upstream.calls[0].url) == "http://other.test/p"
    assert "x-target-url" not in upstream.calls[0].headers


def test_no_target_is_400(client):
    app.state.proxy.apply(AppConfig())
    assert client.get("/x").status_code == 400


def test_cache_miss_then_hit_skips_upstream(client, upstream):
    a = client.get("/c?x=1")
    b = client.get("/c?x=1")
    assert (a.headers["x-proxy-cache"], b.headers["x-proxy-cache"]) == ("MISS", "HIT")
    assert b.json() == {"ok": True} and b.headers["content-type"] == "application/json"
    assert len(upstream.calls) == 1


def test_only_get_200_is_cached(client, upstream):
    client.post("/c")
    assert "x-proxy-cache" not in client.post("/c").headers
    upstream.reply = lambda r: httpx.Response(404, json={"no": 1})
    client.get("/missing")
    assert client.get("/missing").headers["x-proxy-cache"] == "MISS"
    assert len(upstream.calls) == 4


def test_oversized_body_streams_but_is_not_cached(client, upstream):
    configure(cache=CacheConfig(max_body_bytes=10))
    upstream.reply = lambda r: httpx.Response(200, content=b"x" * 100)
    assert client.get("/big").content == b"x" * 100
    assert client.get("/big").headers["x-proxy-cache"] == "MISS"
    assert len(upstream.calls) == 2


def test_rate_limit_429_before_upstream_with_headers(client, upstream):
    configure(rate_limit=RateLimitConfig(capacity=2, refill_rate=0.001))
    codes = [client.get(f"/r?i={i}").status_code for i in range(3)]
    last = client.get("/r")
    assert codes == [200, 200, 429] and last.status_code == 429
    assert last.headers["x-ratelimit-limit"] == "2" and last.headers["x-ratelimit-remaining"] == "0"
    assert int(last.headers["retry-after"]) >= 1 and len(upstream.calls) == 2


def test_rate_limit_headers_on_success_and_per_route(client):
    configure(rate_limit=RateLimitConfig(capacity=5, refill_rate=1))
    r = client.get("/a")
    assert (r.headers["x-ratelimit-limit"], r.headers["x-ratelimit-remaining"]) == ("5", "4")
    assert client.get("/b").headers["x-ratelimit-remaining"] == "4"


def test_chaos_error_never_touches_upstream(client, upstream):
    configure(chaos=ChaosConfig(error_injection_enabled=True, failure_rate_percentage=1.0, error_status_codes=[503]))
    r = client.get("/x")
    assert r.status_code == 503 and r.json()["error"] == "chaos_injected" and not upstream.calls
    assert "x-ratelimit-limit" in r.headers


def test_rate_limit_runs_before_chaos_and_cache(client, upstream):
    configure(rate_limit=RateLimitConfig(capacity=1, refill_rate=0.001))
    client.get("/z")  # fills the cache
    assert client.get("/z").status_code == 429  # a cache hit would have been 200


def test_chaos_runs_before_cache(client, upstream):
    client.get("/z")
    configure(chaos=ChaosConfig(error_injection_enabled=True, failure_rate_percentage=1.0))
    assert client.get("/z").status_code in (500, 502, 503, 504)


def test_upstream_down_is_502_and_timeout_is_504(client, upstream):
    def boom(r):
        raise httpx.ConnectError("refused")

    upstream.reply = boom
    assert client.get("/x").status_code == 502

    def slow(r):
        raise httpx.ReadTimeout("slow")

    upstream.reply = slow
    assert client.get("/x").status_code == 504


def test_response_headers_sanitised_and_cookies_kept(client, upstream):
    upstream.reply = lambda r: httpx.Response(
        200, content=b"hi", headers=[("set-cookie", "a=1"), ("set-cookie", "b=2"), ("x-up", "1")]
    )
    r = client.get("/h")
    assert r.headers.get_list("set-cookie") == ["a=1", "b=2"] and r.headers["x-up"] == "1"


def test_metrics_recorded(client):
    client.get("/m")
    client.get("/m")
    s = app.state.proxy.metrics.snapshot(0, 1)
    assert (s["total_requests"], s["cache_hits"], s["cache_misses"]) == (2, 1, 1)
