"""One error format for every failure.

    {"detail": <message or details>, "code": "<machine readable>", "request_id": "<id>"}

`detail` is unchanged from before, so existing pages keep working. `code` is new and stable;
`request_id` is the same id as the X-Request-ID response header and the log lines.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.request_context import REQUEST_ID_HEADER

log = logging.getLogger("app.errors")

_CODES = {
    400: "bad_request", 401: "not_signed_in", 403: "forbidden", 404: "not_found", 405: "method_not_allowed",
    409: "conflict", 413: "too_large", 415: "unsupported_media_type", 422: "invalid_request",
    429: "rate_limited", 503: "unavailable",
}
INTERNAL_MESSAGE = "Something went wrong on our side. If you ask for help, quote the request id."


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def error_body(request: Request, detail, code: str) -> dict:
    return {"detail": detail, "code": code, "request_id": _rid(request)}


def _code_for(status: int, detail) -> str:
    if isinstance(detail, dict) and isinstance(detail.get("code"), str):
        return detail["code"]  # routes that already name their problem keep their own code
    return _CODES.get(status, f"http_{status}")


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            error_body(request, exc.detail, _code_for(exc.status_code, exc.detail)),
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            error_body(request, jsonable_encoder(exc.errors()), "validation_error"), status_code=422
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            error_body(request, INTERNAL_MESSAGE, "internal_error"),
            status_code=500,
            headers={REQUEST_ID_HEADER: _rid(request)},  # this response skips the middleware, so add the header here
        )
