#!/bin/sh
# Starts the API. Before that it brings the database up to date, unless RUN_MIGRATIONS=false
# (use that when migrations are run as their own step, or when several copies start at once).
set -e

if [ "${RUN_MIGRATIONS:-true}" != "false" ]; then
    echo "Applying database migrations..."
    alembic upgrade head
fi

exec uvicorn app.main:app \
    --host 0.0.0.0 --port "${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-1}" \
    --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}"
