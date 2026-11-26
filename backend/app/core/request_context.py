"""The id of the request being handled, so every log line and every error can quote it."""

import re
import uuid
from contextvars import ContextVar

REQUEST_ID_HEADER = "X-Request-ID"
_VALID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def new_request_id() -> str:
    return uuid.uuid4().hex


def clean_request_id(value: str | None) -> str:
    """Keep an id sent by a caller only if it is short and made of safe characters (it ends up in logs)."""
    return value if value and _VALID.match(value) else new_request_id()
