# Changelog

All notable changes are listed here. Format: [Keep a Changelog](https://keepachangelog.com),
versions follow [Semantic Versioning](https://semver.org).

## [Unreleased]

### Security
- The local admin login is no longer written in the repository. It is made randomly on first start, saved in the git-ignored `.env`, and `setup_admin.py` refuses to run when `APP_ENV=production`. The old published admin account is switched off on machines that used it. Change that password anywhere it was reused.

### Changed
- **Breaking for old pages and scripts:** the API now lives under `/api/v1` (`/api/v1/auth/login`, `/api/v1/brands`, ...). `/health` and `/health/db` stay at the root. The pages and scripts were updated; reload any open page. Old addresses answer 404.
- `start-adbanao` and `stop-adbanao` now only stop AdBanao's own servers on ports 8000 and 5173. If another program uses a port, they say which one and leave it running instead of killing it. They ask it to stop politely first.
- PostgreSQL in Docker is now the default database for a new setup (`.env.example`, `apply-fix`, the start scripts, the settings default). The start script starts the container, waits for it and explains Docker problems. SQLite remains an optional quick start: `./apply-fix.sh --sqlite`. To switch an existing SQLite setup: `./apply-fix.sh --postgres`, then `make seed`. Goal P3 done.

### Added
- Goal P5: photos are stored through `app/storage` (local folder or S3-compatible bucket such as Cloudflare R2; `STORAGE_BACKEND`, `S3_*`). The database stores the same key either way. Online the API refuses to start without a bucket. CI tests the S3 code against MinIO.
- Goal P4: the API has a Dockerfile (non-root, health check, migrations at start), exact hash-pinned packages (`requirements.in` compiled to `requirements.txt` by the CI job `lock`), `COOKIE_DOMAIN`, and refuses unsafe production settings. CI job `docker-image` runs the image. See `docs/29-deploying-the-api.md`. Install now uses `pip install --require-hashes -r backend/requirements-dev.txt`.
- API foundations (F8): every answer has an `X-Request-ID`; every error has `detail`, `code` and `request_id` (existing pages keep working); one log line per event with the request id, JSON with `LOG_JSON=true`; AI model names are settings (`GEMINI_MODEL`, now `gemini-3.5-flash-lite`, and `GROQ_MODEL`); `GET /health/providers`. See `docs/28-api-conventions.md`.
- CI job `start-script` now runs twice: PostgreSQL in Docker and SQLite.
- CI runs the whole test suite and every migration on PostgreSQL 16 as well as SQLite, and the end-to-end job runs the real API on PostgreSQL. `make test-pg` does the same on the Docker database. First step of goal P3.
- CI job `start-script` runs `apply-fix.sh`, `start-adbanao.sh` and `stop-adbanao.sh` on a fresh SQLite database: API and pages start, the admin is made and can sign in, stop frees the ports, and another program on a port is left running. Also runnable by hand: `scripts/check_start_scripts.sh` (it replaces `.env`).

### Docs
- Production plan: `docs/27-production-plan.md` (React, PostgreSQL and automatic deployment, as the faculty asked), new roadmap milestone M5 (P1 to P11), ADR 0008 (proposed). The old goals S2 and S3 became P4, P6 and P7.
- The faculty demo, the PC test guide and the README now say SQLite is the default and PostgreSQL is optional. The demo has two setups (SQLite, PostgreSQL) and uses the admin login from `.env`.

### Removed
- Leftover `*.bak` backup files, the duplicate `files/` folder and `apply.sh` (nothing used them). `*.bak` is now git-ignored.

### Fixed
- The Bangla headline on the home page is smaller so it no longer overflows or shifts the hero layout.
- The home page nav bar stays at the top while scrolling.
- The home page footer no longer says nothing is saved (accounts are real; only the ad creation page is a prototype).
- Sign-in and sign-up card no longer changes layout when an error message appears: space for the message is reserved. A network failure now shows the short translated message.
- The database viewer port can be changed with `ADMINER_PORT` when 8080 is already in use.

### Added
- "How to start" guide on the ad creation page, with a "Don't show this again" option and a "How to start" button to open it again.
- The run guide now lives in `docs/26-run-adbanao.md` (moved from the project root).
- ADR 0007: the AI proposes the design, our code renders and checks it.
- AI and ad engine plan (`docs/25-ai-and-ad-engine-plan.md`).
- Project tracker (`docs/TRACKER.md`) and `scripts/update_tracker.py`.
- Project documents, backend skeleton and database models.
- Product and brand profiles: input, price and unit cleanup, photo validation, readiness report.
- Grounded product description and ad text generation with fact checking and basic-text fallback.
- Documentation set in `docs/` (17 topic files and an index), decision records, CI workflow, Makefile and developer tooling.

### Added
- User accounts: sign up, sign in, sign out, profile read and update, password change (`/auth/*`, `/users/me`).
- Alembic migrations with an initial schema (`make migrate`).

### Added
- Admin sign-in page with email, password and secret word (migration 0004), `make admin-secret`, gradients on the sign-in and sign-up page.
- Admin console: user roles, account suspension, activity log (migration 0003), `/admin/*` API, CSV downloads, `frontend/admin.html` (light/dark, desktop/phone, English/Bangla), `make admin`, demo admin user, admin end-to-end checks.

### Fixed
- Type error in price validation message (mypy).

### Changed
- README shortened for readers. All other documentation moved into `docs/`.
- Code moved into `core`, `db`, `domain`, `providers`, `api/v1` and `schemas`. Tests moved to `backend/tests`.
