"""Where uploaded files live: local disk for development, an S3-compatible bucket (Cloudflare R2) online.

The database stores only a *key* such as ``products/<sha256>.jpg``. The same key works with both backends,
so moving from disk to a bucket changes no database rows.
"""

from functools import lru_cache
from typing import Protocol

from app.core.config import get_settings
from app.storage.local import LocalStorage
from app.storage.s3 import S3Storage


class Storage(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...

    def get(self, key: str) -> bytes | None: ...

    def exists(self, key: str) -> bool: ...

    def delete(self, key: str) -> None: ...


def build_storage(settings) -> Storage:
    if settings.storage_backend == "s3":
        return S3Storage(
            bucket=settings.s3_bucket,
            endpoint_url=settings.s3_endpoint_url or None,
            access_key=settings.s3_access_key_id,
            secret_key=settings.s3_secret_access_key,
            region=settings.s3_region,
        )
    return LocalStorage(settings.upload_dir)


@lru_cache
def get_storage() -> Storage:
    return build_storage(get_settings())
