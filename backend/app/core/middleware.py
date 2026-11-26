"""Request id and access log, as a plain ASGI middleware (no extra copy of the request body)."""

import logging
import time

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.request_context import REQUEST_ID_HEADER, clean_request_id, request_id_var

access_log = logging.getLogger("app.access")


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        rid = clean_request_id(Headers(scope=scope).get(REQUEST_ID_HEADER))
        scope.setdefault("state", {})["request_id"] = rid  # error handlers outside this middleware read it here
        token = request_id_var.set(rid)
        started = time.perf_counter()
        status = 500

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = rid
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            # The path only: a query string can carry things that must not reach the logs.
            access_log.info(
                "%s %s -> %s",
                scope["method"],
                scope["path"],
                status,
                extra={"method": scope["method"], "path": scope["path"], "status": status,
                       "duration_ms": round((time.perf_counter() - started) * 1000, 1)},
            )
            request_id_var.reset(token)
