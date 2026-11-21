import pytest

pytest.importorskip("pydantic_settings")

from app.core.config import ENV_FILE  # noqa: E402


def test_env_file_is_in_the_repository_root():
    # .env.example sits in the repository root, so the real .env must be looked up there.
    assert (ENV_FILE.parent / ".env.example").exists()
