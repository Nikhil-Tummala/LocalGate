from app.services.cache import LRUCache, make_key


class Clock:
    t = 0.0

    def __call__(self):
        return self.t


def test_key_ignores_query_order_and_method_case():
    assert make_key("get", "http://h/p?b=1&a=2") == make_key("GET", "http://h/p?a=2&b=1")


def test_key_differs_by_method_url_and_body():
    base = make_key("POST", "http://h/p", b"x")
    assert base != make_key("GET", "http://h/p", b"x")
    assert base != make_key("POST", "http://h/q", b"x")
    assert base != make_key("POST", "http://h/p", b"y")


def test_hit_and_ttl_expiry():
    clock = Clock()
    c = LRUCache(10, clock)
    c.put("k", b"body", 200, "text/plain", ttl=5)
    assert c.get("k").body == b"body"
    clock.t = 5.0
    assert c.get("k") is None and len(c) == 0


def test_lru_eviction_respects_recent_use():
    c = LRUCache(2, Clock())
    c.put("a", b"1", 200, None, 60)
    c.put("b", b"2", 200, None, 60)
    c.get("a")  # a is now most recent
    c.put("c", b"3", 200, None, 60)
    assert c.get("b") is None and c.get("a") and c.get("c")


def test_resize_and_clear():
    c = LRUCache(3, Clock())
    for k in "abc":
        c.put(k, b"", 200, None, 60)
    c.resize(1)
    assert len(c) == 1 and c.get("c")
    assert c.clear() == 1 and len(c) == 0
