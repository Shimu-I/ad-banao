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

if creds.app_env() == "production":
    sys.exit("ERROR  setup_admin.py is for your own computer only and refuses to run when APP_ENV=production.")

if creds.ensure():
    EMAIL, PASSWORD, SECRET = creds.load()
    print("NEW admin login saved in .env (it is not committed). Write it down:")
    print(f"  email: {EMAIL}\n  password: {PASSWORD}\n  secret word: {SECRET}")
    creds.write_env({"ADMIN_EMAILS": f"{EMAIL}={SECRET}"})
else:
    EMAIL, PASSWORD, SECRET = creds.load()

problem = password_problem(PASSWORD, EMAIL) or secret_word_problem(SECRET, PASSWORD)
if problem:
    sys.exit(f"ERROR  {problem}  Fix ADBANAO_ADMIN_* in .env.")

with SessionLocal() as db:
    for old in db.scalars(select(User).where(User.email.in_(creds.LEAKED_EMAILS))):
        if old.email != EMAIL:  # the published login must stop working on machines that used it
            old.role, old.is_active = "user", False
            print(f"OK  retired the old published admin account: {old.email}")
    user = db.scalar(select(User).where(User.email == EMAIL))
    made = user is None
    if made:
        user = User(email=EMAIL, display_name="Admin", language="en", password_hash="")
        db.add(user)
    user.password_hash = hash_password(PASSWORD)
    user.admin_secret_hash = hash_password(SECRET)
    user.role = ROLE_ADMIN
    user.is_active = True
    db.commit()
    print(f"OK  admin {'created' if made else 'updated'}: {EMAIL}  (database: {engine.url.render_as_string(hide_password=True)})")
