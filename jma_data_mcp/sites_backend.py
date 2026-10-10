"""Stateless HTTP backend for the Sites Worker; stdio and CLI remain unchanged."""

import hashlib
import hmac
import os

from fastmcp.server.http import StarletteWithLifespan
from starlette.datastructures import Headers
from starlette.middleware import Middleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .server import mcp


class ServiceAuthorization:
    """Authenticate the Worker service, without asserting a visitor identity."""

    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self.token_hash = hashlib.sha256(f"Bearer {token}".encode()).digest()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = Headers(scope=scope)
            supplied_hash = hashlib.sha256(headers.get("authorization", "").encode()).digest()
            if not hmac.compare_digest(supplied_hash, self.token_hash):
                await JSONResponse({"error": "Service authentication required"}, 401)(
                    scope, receive, send
                )
                return
            # This is a service-only endpoint; browsers go through Sites.
            if "origin" in headers:
                await JSONResponse({"error": "Browser access is not allowed"}, 403)(
                    scope, receive, send
                )
                return
        await self.app(scope, receive, send)


def create_app() -> StarletteWithLifespan:
    """Uvicorn factory: fail closed when the runtime service secret is absent."""
    token = os.environ.get("JMA_BACKEND_TOKEN", "")
    if len(token) < 32 or any(not 33 <= ord(c) <= 126 for c in token):
        raise ValueError("Set JMA_BACKEND_TOKEN to a random ASCII token of at least 32 characters")
    return mcp.http_app(
        path="/mcp",
        stateless_http=True,
        # JSON avoids the legacy client's SSE event size limit for large series.
        json_response=True,
        middleware=[Middleware(ServiceAuthorization, token=token)],
    )
