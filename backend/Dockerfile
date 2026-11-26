# Builds the AdBanao API image. Build from the repository root:  docker build -f backend/Dockerfile -t adbanao-api backend
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_ENV=production \
    LOG_JSON=true \
    PORT=8000

WORKDIR /app

# Exact, hash-checked packages only (see requirements.in and docs/29-deploying-the-api.md).
COPY requirements.txt .
RUN pip install --require-hashes -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY docker-entrypoint.sh .

# Run as a normal user, never root. /data is where uploaded photos go until object storage (P5).
RUN useradd --system --uid 10001 --home-dir /app adbanao \
    && mkdir -p /data/uploads && chown -R adbanao /data \
    && chmod +x docker-entrypoint.sh
ENV UPLOAD_DIR=/data/uploads
USER adbanao

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT','8000'),timeout=4)"

ENTRYPOINT ["./docker-entrypoint.sh"]
