"""Repairs .env once so every tool uses the same database and the same admin.

    python scripts/fix_env.py            keep the current database
    python scripts/fix_env.py --sqlite   switch to a local SQLite file (no Docker needed)
"""
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _admin_creds as creds  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
PG = "postgresql://adbanao:adbanao@localhost:5432/adbanao"

if not ENV.exists():
    src = ROOT / ".env.example"
    ENV.write_text(src.read_text() if src.exists() else "")
else:
    shutil.copy(ENV, ROOT / f".env.bak.{int(time.time())}")

lines = ENV.read_text().splitlines()


def get(key):
    for ln in lines:
        if ln.startswith(key + "="):
            return ln.split("=", 1)[1].strip()
    return ""


def put(key, value):
    for i, ln in enumerate(lines):
        if ln.startswith(key + "="):
            lines[i] = f"{key}={value}"
            return
    lines.append(f"{key}={value}")


abs_sqlite = "sqlite:///" + (ROOT / "adbanao.db").as_posix()
cur = get("DATABASE_URL")
if "--sqlite" in sys.argv or not cur or cur.startswith(("sqlite:///./", "sqlite:///adbanao")):
    put("DATABASE_URL", abs_sqlite)  # absolute: same file whatever folder a command runs from
    old = ROOT / "backend" / "adbanao.db"
    if old.exists() and not (ROOT / "adbanao.db").exists():
        shutil.copy(old, ROOT / "adbanao.db")  # keep users created earlier
elif "user:password@" in cur:
    put("DATABASE_URL", PG)  # the placeholder from .env.example never works

put("APP_ENV", "development")
put("FRONTEND_ORIGIN", "http://localhost:5173")
put("ADMIN_EMAILS", f"{creds.EMAIL}={creds.SECRET}")
ENV.write_text("\n".join(lines) + "\n")
print("OK  .env fixed. Database:", get("DATABASE_URL").split("@")[-1])
