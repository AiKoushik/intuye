"""Transport-level protections: request ids, security headers, body size limits."""
from __future__ import annotations

import secrets

from starlette.types import ASGIApp, Message, Receive, Scope, Send

BATCH_PATHS = ("/v1/utterances",)


class SecurityMiddleware:
    def __init__(self, app: ASGIApp, max_body: int, max_batch_body: int) -> None:
        self.app, self.max_body, self.max_batch_body = app, max_body, max_batch_body

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = secrets.token_hex(8)
        limit = self.max_batch_body if scope["path"].startswith(BATCH_PATHS) else self.max_body
        headers = dict(scope.get("headers") or [])
        declared = headers.get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > limit:
            await _reject(send, request_id)
            return

        seen = 0

        async def limited_receive() -> Message:
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > limit:
                    raise _TooLarge()
            return message

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                h = list(message.get("headers", []))
                h += [
                    (b"x-request-id", request_id.encode()),
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"strict-transport-security", b"max-age=63072000; includeSubDomains"),
                ]
                message["headers"] = h
            await send(message)

        scope.setdefault("state", {})["request_id"] = request_id
        try:
            await self.app(scope, limited_receive, send_with_headers)
        except _TooLarge:
            await _reject(send, request_id)


class _TooLarge(Exception):
    pass


async def _reject(send: Send, request_id: str) -> None:
    body = b'{"error":{"code":"payload_too_large","message":"Request body is too large."}}'
    await send({"type": "http.response.start", "status": 413,
                "headers": [(b"content-type", b"application/json"), (b"x-request-id", request_id.encode())]})
    await send({"type": "http.response.body", "body": body})
