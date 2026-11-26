import os
import tempfile

# Use a throwaway in-memory database and upload folder for every test run. This must
# be set before the app modules are imported, because settings and the database
# engine are created at import time.
# Set TEST_DATABASE_URL (a PostgreSQL URL) to run the whole suite on PostgreSQL. CI runs both.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "").strip()
os.environ["DATABASE_URL"] = TEST_DATABASE_URL or "sqlite://"
os.environ["APP_ENV"] = "test"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="adbanao-test-uploads-")
os.environ["ADMIN_EMAILS"] = "boss@example.com=boss-secret-1, Second.Boss@Example.com=second-secret-1, nosecret@example.com"


import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _clean_test_database():
    """A PostgreSQL test database lives on between runs, so start every run from empty tables."""
    if TEST_DATABASE_URL.startswith("postgres"):
        from sqlalchemy import text

        from app.db import models  # noqa: F401
        from app.db.session import Base, engine

        Base.metadata.drop_all(bind=engine)
        with engine.begin() as conn:
            conn.execute(text("drop table if exists alembic_version"))
    yield
