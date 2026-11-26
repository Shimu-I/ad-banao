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


@lru_cache
def get_settings() -> Settings:
    return Settings()
