# ADR 0008: Production base first, with automatic deployment

Status: **proposed** (2026-11-25). Becomes accepted when the owner answers the decisions in [27-production-plan.md](../27-production-plan.md) section 9.

## Context
The faculty asked for a production-ready stack (React and PostgreSQL) and for early deployment, so that new work reaches production by itself. Today the frontend is plain HTML and JavaScript, SQLite is the default database, nothing is deployed, and CI only tests.

## Decision
Before the ad engine, build a production base: PostgreSQL as the default everywhere, a deployable API container, a first live deployment of today's features, and automatic deployment on merge to `main`. Then move the frontend to React and TypeScript (Vite, as in ADR 0005) one page at a time.

Recommended platform, all with free tiers and no card to start: Cloudflare Pages for the React build, Neon for PostgreSQL, Render (free to start) for the API container, Cloudflare R2 for photos, and an own domain with `app.` and `api.` subdomains so the session cookie stays on one site. Alternatives and their costs are in the plan.

## Consequences
- The ad engine starts later, but everything built after this is live from the first day.
- A bad merge can reach the live site; checks, a smoke test after deploy and a rollback step reduce that risk.
- Free hosting sleeps and has small limits, so this is production style, not yet always-on for paying customers.
- Migrations must work with the previous version of the code.
- ADR 0005 stays valid. The old goals S2 and S3 are replaced by P4, P6 and P7.
