# Deploying the API (goal P4)

The API ships as a Docker image built from `backend/Dockerfile`. Nothing here needs a hosting account to try: you can run the image on your own PC.

## Run the image on your PC

```bash
docker compose up -d db                      # the development PostgreSQL
docker build -t adbanao-api backend
docker run --rm --network host \
  -e DATABASE_URL=postgresql://adbanao:CHANGE-ME@localhost:5432/adbanao \
  -e FRONTEND_ORIGIN=https://app.example.com \
  adbanao-api
```

The image starts in production mode, so it refuses the development database password and an `http://` page address (see "Safety checks" below). To try it with the development database, add `-e APP_ENV=development`.

## Environment variables

| Variable | Required online | Meaning |
|---|---|---|
| `APP_ENV` | set to `production` by the image | Production mode: secure cookie, no bootstrap admins, tables only by migrations |
| `DATABASE_URL` | yes | PostgreSQL address (Neon gives one) |
| `FRONTEND_ORIGIN` | yes | Exact address of the page, `https://...`. Only this origin may call the API with the cookie |
| `COOKIE_DOMAIN` | when page and API are on subdomains | e.g. `example.com`, so `app.` and `api.` share the sign-in cookie. Empty locally |
| `GEMINI_API_KEY`, `GROQ_API_KEY` | for AI features | Free keys |
| `GEMINI_MODEL`, `GROQ_MODEL` | no | Model names (providers retire models) |
| `LOG_LEVEL`, `LOG_JSON` | no | The image sets `LOG_JSON=true` |
| `PORT` | no (hosts set it) | Port to listen on, default 8000 |
| `WEB_CONCURRENCY` | no | Worker processes, default 1 |
| `RUN_MIGRATIONS` | no | `false` to skip migrations at start |
| `STORAGE_BACKEND` | `s3` online | `local` (folder `UPLOAD_DIR`, development) or `s3` (bucket). A container's disk is erased on each deploy, so online it must be `s3` |
| `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | with `s3` | Bucket name and its keys (Cloudflare R2: create an API token limited to that bucket) |
| `S3_ENDPOINT_URL`, `S3_REGION` | R2: yes / `auto` | R2: `https://<account id>.r2.cloudflarestorage.com`. Empty for AWS S3 |
| `UPLOAD_DIR` | with `local` | Folder for photos in development |

## Safety checks at start

With `APP_ENV=production` the API refuses to start (and says why) if `FRONTEND_ORIGIN` is not `https://`, `DATABASE_URL` is not PostgreSQL or still has the development password, or `STORAGE_BACKEND` is not `s3` (or its bucket settings are missing), or `ADMIN_EMAILS` is set.

## Migrations

The container runs `alembic upgrade head` before it starts serving. Rules so that a deploy never breaks the running version:

1. A migration must work with the previous code too (add columns as nullable or with a default; remove a column only in a later release, after no code uses it).
2. If several copies start at once, set `RUN_MIGRATIONS=false` on them and run migrations as one separate step.

## Pinned packages

`backend/requirements.in` lists what the app needs; `requirements.txt` is the exact, hash-checked list compiled from it (`requirements-dev.in` and `requirements-dev.txt` likewise, for tests and tools). To change a package: edit the `.in` file and push. The CI job `lock` compiles the files and prints them in its log (also as the `lock-files` artifact); commit those over the `.txt` files. The job fails until the committed files match. Install with `pip install --require-hashes -r backend/requirements-dev.txt`.

## What is tested

CI job `docker-image` builds the image and runs it on PostgreSQL 16: migrations apply, `/health` and `/health/db` answer, an error has the standard body and `X-Request-ID`, the process is not root, and an `http://` page address stops the container. Not yet tested: a real host (goal P6), cookies across free host names, a real Cloudflare R2 bucket (the code is tested against MinIO, which speaks the same protocol; R2 differs in small details, so the first live upload is the real test).

## Photo storage

The database keeps a key such as `products/<sha256>.jpg`; `app/storage` turns it into a file or a bucket object, so moving from disk to a bucket changes no database rows. There is no route that serves photos back yet (goal A5, the ad renderer, reads them through the same storage).
