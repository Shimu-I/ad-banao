"""The same behaviour is required of every storage backend. The S3 case runs only when S3_TEST_* is set (CI starts a moto S3 server)."""

import os
import uuid

import pytest

from app.core.config import Settings
from app.storage import LocalStorage, S3Storage, build_storage
from app.storage.keys import check_key


def _backends(tmp_path):
    yield "local", LocalStorage(tmp_path)
    if os.environ.get("S3_TEST_ENDPOINT"):
        yield (
            "s3",
            S3Storage(
                bucket=os.environ["S3_TEST_BUCKET"],
                endpoint_url=os.environ["S3_TEST_ENDPOINT"],
                access_key=os.environ["S3_TEST_KEY"],
                secret_key=os.environ["S3_TEST_SECRET"],
                region="us-east-1",
            ),
        )


@pytest.fixture(params=["local", "s3"])
def storage(request, tmp_path):
    found = dict(_backends(tmp_path))
    if request.param not in found:
        pytest.skip("S3_TEST_ENDPOINT is not set")
    return found[request.param]


def key():
    return f"products/{uuid.uuid4().hex}.jpg"


def test_put_then_get_returns_the_same_bytes(storage):
    k = key()
    storage.put(k, b"\xff\xd8photo", "image/jpeg")
    assert storage.exists(k)
    assert storage.get(k) == b"\xff\xd8photo"


def test_missing_key_is_absent_not_an_error(storage):
    k = key()
    assert not storage.exists(k)
    assert storage.get(k) is None


def test_delete_removes_and_is_repeatable(storage):
    k = key()
    storage.put(k, b"x", "image/jpeg")
    storage.delete(k)
    storage.delete(k)
    assert not storage.exists(k)


def test_local_storage_leaves_no_temp_files(tmp_path):
    LocalStorage(tmp_path).put("brands/a.png", b"1", "image/png")
    assert [p.name for p in (tmp_path / "brands").iterdir()] == ["a.png"]


@pytest.mark.parametrize("bad", ["../x.jpg", "/etc/passwd", "products/../../x", "a\\b.jpg", "x.jpg", "products/"])
def test_unsafe_keys_are_refused(bad):
    with pytest.raises(ValueError):
        check_key(bad)


def test_settings_choose_the_backend(tmp_path):
    assert isinstance(build_storage(Settings(_env_file=None, upload_dir=str(tmp_path))), LocalStorage)


def test_production_requires_a_bucket():
    base = dict(
        app_env="production",
        admin_emails="",
        frontend_origin="https://a.example.com",
        database_url="postgresql://u:strong@db.example.com/x",
    )
    assert any("STORAGE_BACKEND" in p for p in Settings(_env_file=None, **base).production_problems())
    s3 = Settings(_env_file=None, storage_backend="s3", **base)
    assert any("S3_BUCKET" in p for p in s3.production_problems())
    full = Settings(
        _env_file=None, storage_backend="s3", s3_bucket="b", s3_access_key_id="k", s3_secret_access_key="s", **base
    )
    assert full.production_problems() == []
