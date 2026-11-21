# Changelog

All notable changes are listed here. Format: [Keep a Changelog](https://keepachangelog.com),
versions follow [Semantic Versioning](https://semver.org).

## [Unreleased]

### Added
- Project documents, backend skeleton and database models.
- Product and brand profiles: input, price and unit cleanup, photo validation, readiness report.
- Grounded product description and ad text generation with fact checking and basic-text fallback.
- Documentation set in `docs/` (17 topic files and an index), decision records, CI workflow, Makefile and developer tooling.

### Added
- User accounts: sign up, sign in, sign out, profile read and update, password change (`/auth/*`, `/users/me`).
- Alembic migrations with an initial schema (`make migrate`).

### Fixed
- Type error in price validation message (mypy).

### Changed
- README shortened for readers. All other documentation moved into `docs/`.
- Code moved into `core`, `db`, `domain`, `providers`, `api/v1` and `schemas`. Tests moved to `backend/tests`.
