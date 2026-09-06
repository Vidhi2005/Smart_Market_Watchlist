"""
Security-headers and request-body-size middleware for the API.

Applies to the backend's own JSON responses and to /docs's Swagger UI HTML
(the CSP is deliberately permissive enough for that page specifically, since
the project owner asked to keep API docs available rather than disable
them). Does not touch the separately-deployed Next.js frontend.

Implemented as plain ASGI middleware (a callable class), not
starlette.middleware.base.BaseHTTPMiddleware — BaseHTTPMiddleware runs the
downstream app in a separate anyio task via call_next(), which can bind an
in-flight database connection/future to a different task than the one the
ORM/driver expects (surfaces as asyncpg's "attached to a different loop"
under certain async test/runtime setups). Plain ASGI middleware runs
in-process with no extra task, avoiding that class of issue entirely.
"""
from __future__ import annotations

from app.config import settings

# FastAPI's default /docs (Swagger UI) injects inline <script>/<style> and
# loads its JS/CSS bundle from cdn.jsdelivr.net — both are required here or
# /docs breaks under this CSP.
_CSP = (
    "default-src 'self'; "
    "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
)


class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        is_https = scope.get("scheme") == "https"

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.append((b"x-content-type-options", b"nosniff"))
                headers.append((b"referrer-policy", b"strict-origin-when-cross-origin"))
                headers.append((b"x-frame-options", b"DENY"))
                headers.append((b"content-security-policy", _CSP.encode("latin-1")))
                if is_https:
                    headers.append(
                        (b"strict-transport-security", b"max-age=63072000; includeSubDomains")
                    )
            await send(message)

        await self.app(scope, receive, send_wrapper)


class BodySizeLimitMiddleware:
    """
    Rejects requests whose declared Content-Length exceeds the configured
    limit. Only catches a truthful Content-Length header, not a
    chunked-transfer bypass — acceptable here since no reverse-proxy layer
    is being introduced by this change.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                size = int(content_length)
            except ValueError:
                size = 0
            if size > settings.max_body_size_bytes:
                await send({
                    "type": "http.response.start",
                    "status": 413,
                    "headers": [(b"content-type", b"application/json")],
                })
                await send({
                    "type": "http.response.body",
                    "body": b'{"detail":"Request body too large"}',
                })
                return

        await self.app(scope, receive, send)
