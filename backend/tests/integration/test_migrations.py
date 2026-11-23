"""The migration must build exactly the schema the models describe."""

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("alembic")
pytest.importorskip("pydantic_settings")

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


def test_upgrade_matches_models_and_downgrades(tmp_path):
    url = f"sqlite:///{tmp_path / 'm.db'}"
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
    "values ('Old Brand', '[]', '[]', '[]', 0, '2026-01-01', '2026-01-01')"
)
_USER = (
    "insert into users (email, password_hash, display_name, language, created_at, updated_at) "
    "values ('old@example.com', 'x', 'Old', 'en', '2026-01-01', '2026-01-01')"
)


def test_old_brands_are_given_to_the_oldest_user(tmp_path):
    from sqlalchemy import text

    url = f"sqlite:///{tmp_path / 'o.db'}"
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


def test_old_brands_without_any_user_stop_the_migration(tmp_path):
    from sqlalchemy import text

    url = f"sqlite:///{tmp_path / 'n.db'}"
    command.upgrade(_config(url), "0001")
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text(_BRAND))
    with pytest.raises(RuntimeError, match="no users"):
        command.upgrade(_config(url), "head")
    engine.dispose()


def test_0003_keeps_existing_users_and_logs_their_signup(tmp_path):
    from sqlalchemy import text

    url = f"sqlite:///{tmp_path / 'a.db'}"
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
