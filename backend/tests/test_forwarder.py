import httpx
from starlette.datastructures import Headers

from app.services.forwarder import clean_request_headers, clean_response_headers


def test_request_strips_hop_by_hop_and_control_headers():
    h = Headers({
        "host": "localhost:8000", "connection": "close, x-foo", "x-foo": "1", "keep-alive": "5",
        "transfer-encoding": "chunked", "x-target-url": "http://t", "content-length": "3",
        "accept": "*/*", "authorization": "Bearer t",
    })
    out = clean_request_headers(h)
    assert out == {"accept": "*/*", "authorization": "Bearer t", "accept-encoding": "gzip, deflate"}


def test_response_strips_hop_by_hop_but_keeps_repeated_headers():
    h = httpx.Headers([
        ("set-cookie", "a=1"), ("set-cookie", "b=2"), ("content-encoding", "gzip"),
        ("content-length", "9"), ("transfer-encoding", "chunked"), ("x-y", "z"),
    ])
    assert clean_response_headers(h) == [("set-cookie", "a=1"), ("set-cookie", "b=2"), ("x-y", "z")]


def test_open_upstream_streams_without_reading_body():
    from app.services.forwarder import open_upstream
    import asyncio

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST" and request.content == b"hi" and "x-target-url" not in request.headers
        return httpx.Response(201, content=b"streamed")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            r = await open_upstream(c, "POST", "http://up/x", {"a": "b"}, b"hi")
            assert r.status_code == 201
            assert await r.aread() == b"streamed"
            await r.aclose()

    asyncio.run(run())
