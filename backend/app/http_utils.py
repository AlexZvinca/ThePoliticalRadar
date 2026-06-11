from __future__ import annotations

import httpx


def describe_http_error(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        response = exc.response
        detail = response.text.strip().replace("\n", " ")[:180]
        suffix = f": {detail}" if detail else ""
        return f"HTTP {response.status_code} from {response.url}{suffix}"
    if isinstance(exc, httpx.ConnectError):
        return "connection failed"
    if isinstance(exc, httpx.TimeoutException):
        return "request timed out"
    if isinstance(exc, httpx.HTTPError):
        return exc.__class__.__name__
    if str(exc):
        return str(exc)
    return exc.__class__.__name__
