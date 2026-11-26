"""The migration must build exactly the schema the models describe."""

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("alembic")
pytest.importorskip("pydantic_settings")

import os  # noqa: E402
import uuid  # noqa: E402
from pathlib import Path  # noqa: E402

from alembic.autogenerate import compare_metadata  # noqa: E402
from alembic.config import Config  # noqa: E402
from alembic.migration import MigrationContext  # noqa: E402
from sqlalchemy import create_engine, inspect  # noqa: E402

from alembic import command  # noqa: E402
from app.db import models  # noqa: E402,F401
from app.db.session import Base  # noqa: E402

BACKEND = Path(__file__).resolve().parents[2]


def _config(url: str) -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


_PG = os.environ.get("TEST_DATABASE_URL", "").strip()


@pytest.fixture(params=["sqlite", "postgres"])
def db_url(request, tmp_path):
    """An empty database for one test: a SQLite file, or a throwaway PostgreSQL database."""
    if request.param == "sqlite":
        yield f"sqlite:///{tmp_path / 'm.db'}"
        return
    if not _PG.startswith("postgres"):
        pytest.skip("set TEST_DATABASE_URL to a PostgreSQL URL to run this on PostgreSQL")
    from sqlalchemy import text
    from sqlalchemy.engine import make_url

    from app.db.url import normalize_database_url

    admin_url = make_url(normalize_database_url(_PG))
    name = "migtest_" + uuid.uuid4().hex[:10]
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'create database "{name}"'))
    try:
        yield admin_url.set(database=name).render_as_string(hide_password=False)
    finally:
        with admin.connect() as conn:
            conn.execute(text(f'drop database if exists "{name}" with (force)'))
        admin.dispose()


def test_upgrade_matches_models_and_downgrades(db_url):
    url = db_url
    command.upgrade(_config(url), "head")

    engine = create_engine(url)
    tables = set(inspect(engine).get_table_names())
    assert {"users", "user_sessions", "brands", "products", "ads"} <= tables

    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == [], f"models and migration disagree: {diff}"
    engine.dispose()

    command.downgrade(_config(url), "base")
    engine = create_engine(url)
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    engine.dispose()


_BRAND = (
    "insert into brands (name, primary_colors, secondary_colors, fonts, is_archived, created_at, updated_at) "
    "values ('Old Brand', '[]', '[]', '[]', false, '2026-01-01', '2026-01-01')"
)
_USER = (
    "insert into users (email, password_hash, display_name, language, created_at, updated_at) "
    "values ('old@example.com', 'x', 'Old', 'en', '2026-01-01', '2026-01-01')"
)


def test_old_brands_are_given_to_the_oldest_user(db_url):
    from sqlalchemy import text

    url = db_url
    command.upgrade(_config(url), "0001")
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text(_USER))
        conn.execute(text(_BRAND))
    command.upgrade(_config(url), "head")
    with engine.connect() as conn:
        owner = conn.execute(text("select user_id from brands")).scalar()
        uid = conn.execute(text("select id from users")).scalar()
    assert owner == uid
    engine.dispose()


def test_old_brands_without_any_user_stop_the_migration(db_url):
    from sqlalchemy import text

    url = db_url
    command.upgrade(_config(url), "0001")
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text(_BRAND))
    with pytest.raises(RuntimeError, match="no users"):
        command.upgrade(_config(url), "head")
    engine.dispose()


def test_0004_adds_secret_word_columns_and_unverifies_old_sessions(db_url):
    from sqlalchemy import text

    url = db_url
    command.upgrade(_config(url), "0003")
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text(_USER))
        conn.execute(text(
            "insert into user_sessions (user_id, token_hash, created_at, expires_at) "
            "values (1, 'h', '2026-01-01', '2030-01-01')"
        ))
    command.upgrade(_config(url), "head")
    with engine.connect() as conn:
        assert conn.execute(text("select admin_secret_hash from users")).scalar() is None
        assert bool(conn.execute(text("select admin_verified from user_sessions")).scalar()) is False
    command.downgrade(_config(url), "0003")
    assert "admin_verified" not in {c["name"] for c in inspect(engine).get_columns("user_sessions")}
    assert "admin_secret_hash" not in {c["name"] for c in inspect(engine).get_columns("users")}
    engine.dispose()


def test_0003_keeps_existing_users_and_logs_their_signup(db_url):
    from sqlalchemy import text

    url = db_url
    command.upgrade(_config(url), "0002")
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text(_USER))
    command.upgrade(_config(url), "head")
    with engine.connect() as conn:
        role, active = conn.execute(text("select role, is_active from users")).one()
        events = conn.execute(text("select event_type, user_id from activity_events")).all()
    assert role == "user" and bool(active) is True
    assert [e[0] for e in events] == ["signup"]

    command.downgrade(_config(url), "0002")
    cols = {c["name"] for c in inspect(engine).get_columns("users")}
    assert "role" not in cols and "is_active" not in cols
    assert "activity_events" not in inspect(engine).get_table_names()
    engine.dispose()
