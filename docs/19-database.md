# Database

How the database is designed, how it is built, and how to change it. Everything here matches the code in `backend/app/db/models.py` and `backend/alembic/versions/`. For the plan of tables that do not exist yet, see the last section.

## At a glance

| Question | Answer |
| --- | --- |
| Which database? | PostgreSQL for real use (Supabase or Neon free tier, or Docker on your machine). SQLite for quick local runs and for automated tests |
| How is it accessed? | SQLAlchemy 2 (the models), never hand-written SQL in routes |
| How is the schema created? | Alembic migrations (`make migrate`). In development and tests, the app also creates missing tables at startup. In production it does not |
| How many tables? | 8 |
| Where is the connection set? | `DATABASE_URL` in `.env` (template in `.env.example`) |
| Who owns each row? | A user owns their sessions and their brands. Products and ads belong to a user through their brand. Every route checks this, and another user's id answers "not found" |

## Tables and how they connect

```mermaid
erDiagram
    users ||--o{ user_sessions : "signs in with"
    users ||--o{ brands : owns
    users ||--o{ activity_events : "is recorded in"
    brands ||--o{ products : has
    products ||--o{ ads : "advertised by"
    ads ||--o{ verification_reports : "checked by"
    verification_reports ||--o{ verification_checks : contains

    users {
        int id PK
        string email UK
        string password_hash
        string display_name
        string language
        string role
        bool is_active
    }
    activity_events {
        int id PK
        int user_id FK
        int actor_id FK
        string event_type
        datetime created_at
    }
    user_sessions {
        int id PK
        int user_id FK
        string token_hash UK
        datetime expires_at
    }
    brands {
        int id PK
        int user_id FK
        string name
        bool is_archived
    }
    products {
        int id PK
        int brand_id FK
        string name
        decimal price
        string image_sha256
        bool is_archived
    }
    ads {
        int id PK
        int product_id FK
        string status
        string content_hash
        string approved_content_hash
    }
    verification_reports {
        int id PK
        int ad_id FK
        string content_hash
    }
    verification_checks {
        int id PK
        int report_id FK
        string module
        string result
        string severity
    }
```

Accounts (`users`, `user_sessions`) and content (`brands` down to `verification_checks`) are joined by `brands.user_id`. Ownership flows down: a user owns brands, a brand has products, a product has ads, an ad has reports, a report has checks.

## Table by table

Types are the SQLAlchemy types. "Null" means the column may be empty. Every table has an integer `id` primary key.

### `users`

One row per account.

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `email` | string(254) | no | Unique. Stored in lower case, so `Rina@x.com` and `rina@x.com` are the same account |
| `password_hash` | string(300) | no | `scrypt$N$r$p$salt$hash`. The password itself is never stored |
| `display_name` | string(100) | no | Shown in the app |
| `business_name` | string(200) | yes | Profile |
| `phone` | string(30) | yes | Profile |
| `language` | string(5) | no | `en` or `bn` |
| `role` | string(10) | no | `user` (default) or `admin`. Only changed by an admin or the command line. Added by migration 0003 |
| `is_active` | boolean | no | `false` = suspended: cannot sign in, sessions deleted. Added by migration 0003 |
| `admin_secret_hash` | string(300) | yes | scrypt hash of an admin's secret word (second sign-in factor). Empty for normal users. Migration 0004 |
| `created_at`, `updated_at` | datetime with time zone | no | `updated_at` changes on every edit |

### `user_sessions`

One row per signed-in browser. Signing out deletes the row, which ends that session at once.

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `user_id` | integer | no | Foreign key to `users`. **Deleting a user deletes their sessions** (CASCADE). Indexed |
| `token_hash` | string(64) | no | Unique. SHA-256 of the random token held in the browser cookie. The token itself is never stored, so a copy of the database cannot be used to sign in |
| `created_at` | datetime | no | |
| `expires_at` | datetime | no | 14 days after sign-in. Expired rows are rejected and removed when next used |
| `admin_verified` | boolean | no | `true` only for sessions made on the admin sign-in page (email + password + secret word). Migration 0004 |

### `activity_events`

One line per thing that happened, for the admin Activity Log. Added by migration 0003. See [22-admin.md](22-admin.md).

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `user_id` | integer | yes | Who it is about. Foreign key to `users`, **SET NULL**. Empty for a failed sign-in with an unknown email. Indexed |
| `actor_id` | integer | yes | The admin, when an admin did it. Foreign key to `users`, SET NULL |
| `event_type` | string(40) | no | For example `login`, `brand_created`, `admin_suspended`. Indexed |
| `detail` | string(300) | yes | Short text such as a brand name or the changed field names. Never a password or an email typed by a stranger |
| `created_at` | datetime | no | Indexed |

### `brands`

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `user_id` | integer | no | The owner. Foreign key to `users`, **RESTRICT**. Indexed. Added by migration 0002 |
| `name` | string(200) | no | Indexed |
| `primary_colors`, `secondary_colors` | JSON list | no | Hex codes |
| `fonts` | JSON list | no | |
| `logo_path` | string(500) | yes | File location, not the file |
| `tone_notes` | text | yes | |
| `is_archived` | boolean | no | Archive instead of delete |
| `created_at`, `updated_at` | datetime | no | |

### `products`

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `brand_id` | integer | no | Foreign key to `brands`, **RESTRICT** (a brand with products cannot be deleted). Indexed |
| `name` | string(300) | no | |
| `description` | text | yes | |
| `price`, `original_price` | decimal(12,2) | yes | Exact decimals, never floating point. Empty so an unfinished profile can be saved. Generation is blocked until price exists |
| `currency` | string(3) | no | Default `BDT` |
| `unit` | string(50) | yes | Cleaned form such as `500 g` |
| `specs` | JSON object | no | Free facts, for example size or material |
| `allowed_claims` | JSON list | no | Claims the owner confirms are true |
| `key_features` | JSON list | no | Selling points typed by the user. Text generation is allowed to use only these facts |
| `image_path` | string(500) | yes | |
| `image_sha256` | string(64) | yes | Fingerprint of the original photo. Used to prove the photo was never changed |
| `is_archived` | boolean | no | |
| `created_at`, `updated_at` | datetime | no | |

### `ads`

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `product_id` | integer | no | Foreign key to `products`, **RESTRICT**. Indexed |
| `headline` | string(300) | yes | |
| `caption`, `description` | text | yes | |
| `language` | string(10) | no | |
| `template_name` | string(100) | yes | |
| `rendered_image_path` | string(500) | yes | |
| `status` | string(20) | no | `draft`, `needs_fix`, `verified` or `approved` |
| `content_hash` | string(64) | yes | Fingerprint of the ad's current text and image. Changes whenever the ad is edited |
| `approved_content_hash` | string(64) | yes | The fingerprint at the moment a person approved |
| `approved_at` | datetime | yes | |
| `created_at`, `updated_at` | datetime | no | |

**Approval rule.** An ad counts as approved only if its status is `approved` **and** `approved_content_hash` equals `content_hash`. Edit the ad and the two differ, so the approval silently stops being valid. No code has to remember to "cancel" it.

### `verification_reports`

One report per check run on an ad.

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `ad_id` | integer | no | Foreign key to `ads`, **CASCADE**. Indexed |
| `content_hash` | string(64) | yes | Which version of the ad this report covers, so stale reports can be recognised |
| `created_at` | datetime | no | |

### `verification_checks`

One row per check inside a report (price, text, claims, brand, photo).

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `report_id` | integer | no | Foreign key to `verification_reports`, **CASCADE**. Indexed |
| `module` | string(20) | no | `price`, `ocr`, `claims`, `brand`, `integrity`, `quality` |
| `result` | string(20) | no | `verified`, `issue_found` or `cannot_verify` |
| `severity` | string(20) | yes | `critical`, `warning` or `suggestion`. Empty when verified |
| `message` | text | no | What was found, in plain words |
| `suggestion` | text | yes | How to fix it |
| `evidence` | JSON | yes | For example expected value and found value |

**Overall result of a report** is worked out, not stored: if any check found an issue the report is "issue found"; else if it has no checks or any check could not verify, it is "cannot verify"; otherwise "verified". The worst result wins, and an empty report is never "verified".

## Design rules behind the schema

| Rule | How the schema does it |
| --- | --- |
| Never lose data by accident | Brands and products are archived with `is_archived`. Foreign keys to them use RESTRICT, so the database refuses a delete that would orphan an ad |
| Child records go with their parent | Sessions, reports and checks use CASCADE |
| Money is exact | `Numeric(12,2)`, not float |
| Enums are portable | Stored as short text, not a database-specific enum type, so SQLite and PostgreSQL behave the same and adding a value does not need an `ALTER TYPE` |
| Flexible facts without extra tables | JSON columns for colors, fonts, specs, features and evidence |
| Passwords and tokens are not recoverable | Passwords are salted scrypt hashes. Session tokens are stored only as SHA-256 |
| Times are in UTC | All timestamps are stored with a time zone |
| The original photo is provable | Its SHA-256 is stored beside the path |

## How the database is built

```mermaid
flowchart LR
    M[models.py<br/>the single source of truth] --> A[Alembic migration<br/>versions/0001_initial_schema.py]
    A -->|make migrate| DB[(PostgreSQL / SQLite)]
    M --> T[Test: migration must match models]
    A --> T
```

1. **Models** in `backend/app/db/models.py` describe the tables in Python.
2. **Migrations** in `backend/alembic/versions/` are numbered scripts that create or change tables. `0001_initial_schema.py` builds all 7 tables. `0002_brand_owner.py` adds `brands.user_id` (existing brands go to the oldest user; if there are brands and no users, it stops with a message instead of guessing). Each script has `upgrade` and `downgrade`.
3. **A test** (`backend/tests/integration/test_migrations.py`) builds a fresh database from the migrations and fails if it differs from the models. That stops the two from drifting apart.
4. **The URL helper** (`backend/app/db/url.py`) accepts `postgres://` and `postgresql://` links as given by Supabase and Neon and converts them for the driver.
5. **The session** (`backend/app/db/session.py`) creates the engine once and gives each request its own database session, closed after the request. For PostgreSQL it checks connections before use, because free hosts close idle ones.

## Everyday commands

```bash
make db-up        # start PostgreSQL in Docker (needs Docker)
make migrate      # create or upgrade the tables
```

Use PostgreSQL by putting this in `.env`:

```text
DATABASE_URL=postgresql://adbanao:adbanao@localhost:5432/adbanao
```

Look inside the database:

```bash
# SQLite (the default, file adbanao.db in backend/ or where you started the server)
sqlite3 adbanao.db ".tables"
sqlite3 adbanao.db "select id, email, display_name from users;"

# PostgreSQL in Docker
docker compose exec db psql -U adbanao -d adbanao -c "\dt"
docker compose exec db psql -U adbanao -d adbanao -c "select id, email from users;"
```

## How to change the schema

1. Edit the model in `models.py`.
2. From `backend/`, run `alembic revision --autogenerate -m "short description"`.
3. **Read the generated file.** Autogenerate misses some things (renames look like a drop and an add). Fix it by hand if needed.
4. Run `make migrate` on a copy of your data, then `make test`. The migration test must pass.
5. Commit the model and the migration together, in one pull request.

Never edit a migration that has already been merged. Add a new one.

**One-time note for older local databases.** Databases created before migrations existed were built by the app directly. Delete the local `adbanao.db` file and run `make migrate` (there is no data worth keeping yet).

## What is tested and what is not

| Checked | By what |
| --- | --- |
| Models behave (archive rule, approval expiry, worst-result-wins) | `test_models.py`, on SQLite |
| Migration builds the same schema as the models, and downgrades cleanly | `test_migrations.py`, on SQLite |
| Accounts and sessions through the API | `test_auth_api.py`, on SQLite |
| One user cannot see, change or add to another user's brands and products (three users) | `test_ownership.py`, on SQLite. Also the API check in `scripts/smoke_test.py` on SQLite and PostgreSQL |
| The ownership migration moves old brands to the oldest user, and refuses when there is no user | `test_migrations.py` |
| Migration, server and API checks on PostgreSQL 16 in Docker, and downgrade then upgrade again (owner's machine, 2026-11-22) | `scripts/check_my_machine.sh --postgres` |
| **Not yet tested:** a hosted database (Supabase or Neon). Connection strings and limits can differ | Put its URL in `.env`, run `make migrate`, and re-run the check script |

## Not built yet (planned)

These come from the roadmap and [18-pages-and-user-flow.md](18-pages-and-user-flow.md). They are listed so nobody assumes they exist.

| Planned change | Goal | Why |
| --- | --- | --- |
| Ad versions table (scene JSON, one row per edit) | A5, A6 | Undo and redo, and a fingerprint per version |
| Overrides (user's written reason for ignoring a check) | V5 | Recorded and shown on the approve screen |
| Password reset tokens | later | Reset by email |
| Rate-limit or login-attempt record | S4 | Slow down password guessing |
| Brand logo variants (light, dark, icon) | U9 | Settings page |
| Indexes on `ads.status` and `products.is_archived` | when lists get long | Dashboard filters |

Each of these arrives as its own migration.
