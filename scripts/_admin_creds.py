"""The admin login used by the local start scripts.

Nothing secret lives in this file. The values come from the environment or from the
git-ignored `.env` file in the project root:

    ADBANAO_ADMIN_EMAIL, ADBANAO_ADMIN_PASSWORD, ADBANAO_ADMIN_SECRET

If they are missing, `ensure()` makes new random ones and saves them in `.env` (once).
"""
import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
KEYS = ("ADBANAO_ADMIN_EMAIL", "ADBANAO_ADMIN_PASSWORD", "ADBANAO_ADMIN_SECRET")
DEFAULT_EMAIL = "admin@adbanao.test"
# The login that used to be committed to this public repository. It is burned: never reuse it.
LEAKED_EMAILS = ("admin@admin-adbanao.com",)


def read_env(path: Path = ENV) -> dict[str, str]:
    values: dict[str, str] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return values


def write_env(updates: dict[str, str], path: Path = ENV) -> None:
    lines = path.read_text().splitlines() if path.exists() else []
    for key, value in updates.items():
        for i, line in enumerate(lines):
            if line.startswith(key + "="):
                lines[i] = f"{key}={value}"
                break
        else:
            lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n")


def get(key: str, path: Path = ENV) -> str:
    return os.environ.get(key) or read_env(path).get(key, "")


def app_env(path: Path = ENV) -> str:
    return (os.environ.get("APP_ENV") or read_env(path).get("APP_ENV", "development")).strip().lower()


def ensure(path: Path = ENV) -> bool:
    """Fill in any missing admin value with a random one saved in .env. True if something was made."""
    made = False
    updates: dict[str, str] = {}
    if not get("ADBANAO_ADMIN_EMAIL", path):
        updates["ADBANAO_ADMIN_EMAIL"] = DEFAULT_EMAIL
    if not get("ADBANAO_ADMIN_PASSWORD", path):
        updates["ADBANAO_ADMIN_PASSWORD"] = secrets.token_urlsafe(12)
    if not get("ADBANAO_ADMIN_SECRET", path):
        updates["ADBANAO_ADMIN_SECRET"] = secrets.token_urlsafe(9)
    if updates:
        write_env(updates, path)
        made = True
    email = (updates.get("ADBANAO_ADMIN_EMAIL") or get("ADBANAO_ADMIN_EMAIL", path)).strip().lower()
    if email in LEAKED_EMAILS:  # an old .env that still points at the published login
        write_env({"ADBANAO_ADMIN_EMAIL": DEFAULT_EMAIL, "ADBANAO_ADMIN_PASSWORD": secrets.token_urlsafe(12),
                   "ADBANAO_ADMIN_SECRET": secrets.token_urlsafe(9)}, path)
        made = True
    return made


def load(path: Path = ENV) -> tuple[str, str, str]:
    return (get("ADBANAO_ADMIN_EMAIL", path).strip().lower(), get("ADBANAO_ADMIN_PASSWORD", path),
            get("ADBANAO_ADMIN_SECRET", path))
