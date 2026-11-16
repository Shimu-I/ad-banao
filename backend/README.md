# Backend

FastAPI app and PostgreSQL models for AdBanao.

## Run locally

From the repository root:

```
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r backend/requirements-dev.txt
cp .env.example .env               # then edit it
cd backend
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for the interactive API.

If `DATABASE_URL` is not set, the app falls back to a local SQLite file so it still starts. For PostgreSQL, paste the connection string from Supabase or Neon; `postgresql://` and `postgres://` URLs are converted to the psycopg driver automatically.

Uploaded photos and logos are saved under `UPLOAD_DIR` (default `./uploads`, relative to where you start the server).

## Run tests

From the repository root:

```
pytest
```

Tests that need FastAPI, SQLAlchemy or httpx skip themselves if those are not installed.

## API

| Method and path | What it does |
| --- | --- |
| `GET /health`, `GET /health/db` | Liveness and database check |
| `POST /brands` | Create a brand (colors are normalized to `#RRGGBB`) |
| `GET /brands` | List brands (`include_archived`, `limit`, `offset`) |
| `GET /brands/{id}`, `PATCH /brands/{id}` | Read or partly update a brand |
| `POST /brands/{id}/archive`, `/restore` | Archive or restore (there is no delete) |
| `POST /brands/{id}/logo` | Upload a logo (JPEG, PNG or WebP) |
| `POST /products` | Create a product; price text and units are normalized |
| `GET /products` | List products (`brand_id`, `include_archived`, `limit`, `offset`) |
| `GET /products/{id}`, `PATCH /products/{id}` | Read or partly update a product |
| `POST /products/{id}/archive`, `/restore` | Archive or restore (there is no delete) |
| `POST /products/{id}/image` | Upload the product photo; stored untouched with its SHA-256 |
| `GET /products/{id}/readiness` | What is missing, and whether generation and rendering are blocked |

## Input handling

- **Prices:** `1,299`, `1299.00`, `৳1,299`, `BDT 1299`, `Tk. 500`, `$12.99`, `১,২৯৯ টাকা` and `1299/-` all work. A currency symbol sets the currency; a conflict (`$12` with currency `BDT`) is rejected. `12,99` is rejected as ambiguous, and `From ৳999` or `up to 500` cannot be stored as a product price.
- **Units:** `0.5kg` and `500g` both become `500 g`; `1L` and `1000ml` both become `1 l`. Multi-packs such as `2 x 500g` are not supported yet.
- **Photos:** JPEG, PNG or WebP, up to 5 MB and 16 megapixels. Small, transparent, CMYK, very wide, rotated or animated images are accepted with a warning. Files are named by their hash, never by the uploaded name.
- **Incomplete profiles can be saved.** `GET /products/{id}/readiness` lists what is missing: no price blocks generation, no photo blocks rendering, an archived brand blocks both.
- **Prompt-injection check:** text such as "ignore previous instructions" in a name, description or claim is flagged for review. This is a simple pattern check, not protection by itself.

## Layout

```
app/config.py          settings from environment and .env
app/database.py        engine, session, declarative base
app/db_url.py          database URL helpers
app/models.py          Brand, Product, Ad, VerificationReport, VerificationCheck
app/normalize.py       price, discount and unit parsing (no dependencies)
app/images.py          upload validation and storage
app/profile_checks.py  readiness checks for products and brands
app/schemas.py         request and response schemas
app/main.py            FastAPI app factory
app/routers/           health, brands, products
```

## Notes

- Tables are created at startup for now. Alembic migrations replace this later.
- Brands and products are archived, not deleted, while ads still use them. Archived records are read-only until restored.
- An ad approval is tied to the exact ad content; editing the ad invalidates it.
- Verification results are `verified`, `issue_found` or `cannot_verify`. A report with no checks is never "verified".
- Not handled yet: two people editing the same record at once (last write wins), cleaning up photo files that are no longer used, and serving uploaded images over HTTP.
