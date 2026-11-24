"""Creates (or repairs) the fixed admin account straight in the database. Safe to run any time."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT / "backend")
import _admin_creds as creds  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.db.models import User  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.domain.roles import ROLE_ADMIN, secret_word_problem  # noqa: E402
from app.domain.security import hash_password, password_problem  # noqa: E402

problem = password_problem(creds.PASSWORD, creds.EMAIL) or secret_word_problem(creds.SECRET, creds.PASSWORD)
if problem:
    sys.exit(f"ERROR  {problem}")

with SessionLocal() as db:
    user = db.scalar(select(User).where(User.email == creds.EMAIL))
    made = user is None
    if made:
        user = User(email=creds.EMAIL, display_name="Admin", language="en", password_hash="")
        db.add(user)
    user.password_hash = hash_password(creds.PASSWORD)
    user.admin_secret_hash = hash_password(creds.SECRET)
    user.role = ROLE_ADMIN
    user.is_active = True
    db.commit()
    print(f"OK  admin {'created' if made else 'updated'}: {creds.EMAIL}  (database: {engine.url.render_as_string(hide_password=True)})")
