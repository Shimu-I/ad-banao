"""The one place the fixed admin login lives. Override with ADBANAO_ADMIN_* environment variables."""
import os

EMAIL = os.environ.get("ADBANAO_ADMIN_EMAIL", "admin@admin-adbanao.com").strip().lower()
PASSWORD = os.environ.get("ADBANAO_ADMIN_PASSWORD", "admin-aa-bb-demo")
SECRET = os.environ.get("ADBANAO_ADMIN_SECRET", "nov-25-uuuuu")
