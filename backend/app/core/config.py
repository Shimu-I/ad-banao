"""Application settings, read from environment variables and the repo-root .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> the repository root is three folders above this file's folder.
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    app_env: str = "development"
    # PostgreSQL is the default everywhere. Locally: `docker compose up -d db` (the start script does it).
    database_url: str = "postgresql://adbanao:adbanao@localhost:5432/adbanao"
    frontend_origin: str = "http://localhost:5173"
    upload_dir: str = "./uploads"
    gemini_api_key: str = ""
    groq_api_key: str = ""
    # Model names are settings because providers retire models (gemini-2.0-flash shut down on 2026-06-01).
    # Defaults were taken from the providers' pages on 2026-11-26 and not yet tried with a real key.
    gemini_model: str = "gemini-3.5-flash-lite"
    groq_model: str = "llama-3.3-70b-versatile"
    log_level: str = "INFO"
    log_json: bool = False  # set LOG_JSON=true online so a log service can read the lines
    # Comma-separated emails that become admins at sign-up or sign-in. Development and test only.
    admin_emails: str = ""
    # Online, the page (app.example.com) and the API (api.example.com) share one site, so the sign-in cookie
    # is sent with both. Set COOKIE_DOMAIN=example.com (leave empty locally).
    cookie_domain: str = ""

    def production_problems(self) -> list[str]:
        """Settings that must not stay at their development values online. Empty list = fine."""
        if self.app_env != "production":
            return []
        problems = []
        if not self.frontend_origin.startswith("https://"):
            problems.append("FRONTEND_ORIGIN must be an https:// address.")
        if not self.database_url.startswith(("postgresql://", "postgres://", "postgresql+psycopg://")):
            problems.append("DATABASE_URL must be a PostgreSQL address.")
        if "adbanao:adbanao@" in self.database_url:
            problems.append("DATABASE_URL still uses the development password.")
        if self.admin_emails:
            problems.append("ADMIN_EMAILS must be empty (it is ignored online; create admins another way).")
        return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()


def check_production_settings(settings: Settings) -> None:
    problems = settings.production_problems()
    if problems:
        raise RuntimeError("Unsafe production settings:\n- " + "\n- ".join(problems))
