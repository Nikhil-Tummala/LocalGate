"""Proxy forwarder: header sanitisation and streaming upstream requests (httpx)."""
import httpx

# RFC 7230 hop-by-hop headers, a superset of the Host/Connection/Keep-Alive/Transfer-Encoding minimum
HOP_BY_HOP = {
    "host", "connection", "keep-alive", "transfer-encoding", "te", "trailer",
    "trailers", "upgrade", "proxy-authenticate", "proxy-authorization",
}
# Never forwarded upstream: control header, and ones httpx must recompute from the body it sends
_REQUEST_ONLY = {"x-target-url", "content-length", "accept-encoding"}
# httpx decodes bodies for us, so the upstream's encoding/length no longer describe what we send on
_RESPONSE_ONLY = {"content-encoding", "content-length"}


def _drop_set(headers) -> set[str]:
    """HOP_BY_HOP plus any header the sender listed in its Connection header."""
    # ponytail: .get() reads one Connection header (httpx joins repeats, Starlette returns the first)
    named = {t.strip().lower() for t in headers.get("connection", "").split(",") if t.strip()}
    return HOP_BY_HOP | named


def clean_request_headers(headers) -> dict[str, str]:
    drop = _drop_set(headers) | _REQUEST_ONLY
    out = {k: v for k, v in headers.items() if k.lower() not in drop}
    out["accept-encoding"] = "gzip, deflate"  # only encodings httpx can decode
    return out


def clean_response_headers(headers: httpx.Headers) -> list[tuple[str, str]]:
    """Keeps repeated headers (Set-Cookie) as separate entries."""
    drop = _drop_set(headers) | _RESPONSE_ONLY
    return [(k, v) for k, v in headers.multi_items() if k.lower() not in drop]


async def open_upstream(
    client: httpx.AsyncClient, method: str, url: str, headers: dict[str, str], body: bytes
) -> httpx.Response:
    """Send and return once response headers arrive; the body stays unread. Caller must aclose()."""
    request = client.build_request(method, url, headers=headers, content=body or None)
    return await client.send(request, stream=True)
