import re

_SAFE = re.compile(r"^[a-z0-9]+(/[a-z0-9]+)*/[A-Za-z0-9._-]+$")


def check_key(key: str) -> str:
    """Keys are made by the app (folder/hash.ext). Refuse anything that could leave the storage root."""
    if not _SAFE.match(key) or ".." in key:
        raise ValueError(f"unsafe storage key: {key!r}")
    return key
