# Production plan: React, PostgreSQL and early deployment

Written 2026-11-25. Status: **proposal, waiting for the owner's decisions** (section 9). Facts about versions and free tiers were checked on that date (sources at the end). Free tiers change often, so each one is re-checked on the day it is used.

## 1. What the faculty asked

The faculty suggested: use a production-ready framework (React) and PostgreSQL, "not SQL or JavaScript", and **deploy early, so every new piece of work reaches production automatically**.

How we read it:

| Words | Meaning for AdBanao |
| --- | --- |
| "React, not JavaScript" | The frontend becomes React with **TypeScript**, built with Vite, instead of hand-written HTML and JavaScript pages |
| "PostgreSQL, not SQL" | PostgreSQL is the database everywhere (own computer, tests, online). SQLite is no longer the default |
| "Deploy early" | A live address exists soon, with today's features, before the ad engine is built |
| "New work goes to production too" | Continuous deployment: a merged pull request updates the live site by itself |

This does not change the product plan. [ADR 0005](adr/0005-vite-spa-frontend.md) already chose React, TypeScript and Vite, and [03-tech-stack.md](03-tech-stack.md) already names PostgreSQL. What changes is **the order**: we build the production base first, then continue with the ad engine on top of it.

## 2. Where we are today (read from the repository)

| Area | Today | Gap for production |
| --- | --- | --- |
| Frontend | 7 plain HTML pages (home, sign in iframe, profile, dashboard, create prototype, admin login, admin) with inline JavaScript. The pages call the API at `http://<page host>:8000` | Not React. The API address is built into the code. No build step, no tests of the pages themselves |
| Backend | FastAPI, SQLAlchemy 2, Alembic. 8 tables, 4 migrations | No Dockerfile. Dependencies are `>=` ranges, so two installs can differ. No `/api/v1` prefix yet (goal F8) |
| Database | SQLite by default. PostgreSQL works in Docker | CI tests SQLite only. PostgreSQL was checked by hand on the owner's PC (before migrations 0003 and 0004) |
| Sessions | httpOnly cookie, `SameSite=Lax`, `Secure` when `APP_ENV=production` | Works only if the page and the API are on the **same site** (section 6, D5) |
| Uploads | Saved to a local folder (`UPLOAD_DIR`) | Free hosts wipe local files on restart, so photos would vanish |
| CI | Three jobs on every pull request: tests, browser end-to-end, start scripts | Nothing deploys. Default branch is `step-01-repo-setup`, unprotected |
| Security gaps already known | No rate limit on wrong guesses, no password reset | Must be closed before a public launch |

## 3. Target picture

```
Browser
  |  https://app.<domain>            https://api.<domain>
  v                                   v
Cloudflare Pages (React build)  ->  FastAPI in a Docker container (Render or Fly.io)
                                      |                    |
                                      v                    v
                             Neon PostgreSQL        Cloudflare R2 (photos, exported ads)

GitHub: pull request -> checks (tests, lint, browser tests) -> merge to main
        -> automatic deploy of the API, the React build and the database migrations
        -> a smoke test against the live address
```

## 4. The "latest framework" question, with facts (checked 2026-11-25)

| Piece | Latest found | Note |
| --- | --- | --- |
| React | **19.3** (announced 2026-09-09). The React Compiler reached 1.0 (stable) on 2025-10-07 | React 20 is not announced on react.dev |
| Vite | **8.x** (the Vite 8.1 post is dated 2026-06-23; the site shows 8.3.7). Vite 8 uses the Rolldown bundler | Experimental "bundled dev mode" may not work with third party plugins, so we leave it off |
| Tailwind CSS and shadcn/ui | Tailwind v4 with shadcn/ui is a documented Vite and React setup | Same choice as in [03-tech-stack.md](03-tech-stack.md) |
| TypeScript | Current release at scaffold time | Strict mode on |
| Node.js | The current LTS at scaffold time | Pinned in `.nvmrc` and in CI |
| Backend | Python 3.12 (as in CI), latest FastAPI, SQLAlchemy 2, Pydantic 2 | Versions pinned with a lock file (P4) |

**Vite single page app or Next.js?** We keep the Vite app ([ADR 0005](adr/0005-vite-spa-frontend.md)). The signed-in screens need no server rendering, the home page can be generated at build time, and static files host free with no card. Next.js is a good framework, but it adds a second server next to FastAPI. The React team also published two serious security notices about React Server Components in December 2025; a Vite single page app does not use Server Components, so it is not exposed to them.

Smaller choices (made when the scaffold is built, goal P7): React Router or TanStack Router, TanStack Query, React Hook Form with Zod, `openapi-typescript` for the API client, react-i18next, Vitest and Playwright. I did not verify the latest version of each of these; the scaffold pins whatever is current that day.

## 5. Order of work: deploy first, then replace the pages one by one

The idea is a **walking skeleton**: put what exists today online first, wire the automatic deployment, and only then move the frontend to React page by page. Each step is one pull request or a few, and the site stays working throughout. F8 (API foundations) comes first, because P4 builds on it. The old goals S2 (containers) and S3 (staging deployment) are now P4, P6 and P7, so they leave M4 in the [roadmap](07-roadmap.md).

| ID | Goal | Done when | Who |
| --- | --- | --- | --- |
| P1 | Decisions and ADR 0008 | The owner picks hosting, domain, storage (section 9). ADR written | Owner decides, Claude writes |
| P2 | Default branch `main`, protected | Branch renamed, pull requests required, CI must pass before merge | **Owner only** (GitHub settings) |
| P3 | PostgreSQL everywhere | CI runs the whole suite on a PostgreSQL service. Docker Compose is the default developer database. SQLite stays only as an optional quick start, labelled as such. Migrations 0001 to 0004 proven on PostgreSQL in CI | Claude |
| P4 | Make the API deployable | `Dockerfile` (non-root, small image), pinned dependencies with a lock file, `/api/v1` prefix and one error format come first from goal F8; then the API address and allowed origin as settings, migrations as a release step, `make admin` documented for production, health check | Claude |
| P5 | Object storage for photos | A `Storage` interface with local disk and S3-compatible (R2) implementations. Uploads survive a restart. Goal A5 later reuses it | Claude, needs the R2 account |
| P6 | **First live deployment** | Today's pages and API are online: PostgreSQL on Neon, API container on the chosen host, static pages on Cloudflare Pages, cookies working. Sign up, sign in, profile and admin work on the live address | Claude, needs the accounts |
| P7 | **Automatic deployment** | Merge to `main` deploys the API, runs migrations, publishes the pages, then runs a smoke test on the live address. A pull request gets a preview page. Rollback steps written and tried once | Claude |
| P8 | React scaffold. **This is the existing goal U1**, moved up to this point | Vite, React, TypeScript strict, Tailwind v4, shadcn/ui, router, TanStack Query, generated API client, Bangla and English switch, ESLint, Vitest, Playwright, CI job, deployed by P7 | Claude |
| P9 | Move the pages to React, one per pull request | Order: sign in and sign up, profile, home page, dashboard, create page with the guide, admin. The old HTML file is deleted in the same pull request that replaces it. The browser tests move with each page | Claude, owner checks the look |
| P10 | Production hardening | Rate limits (including wrong sign-in guesses), password reset by email, security headers, error tracking (Sentry), logs with request ids, dependency audits (`pip-audit`, `npm audit`, Dependabot), daily database backup to R2 with one restore tried | Claude, needs an email service account |
| P11 | Staging and tagged releases | A second environment and `vMAJOR.MINOR.PATCH` tags, started when real users exist | Later |

After P9 the plan returns to the ad engine (A1 to A7, V1 to V6, U4 to U10). Everything built after that is deployed automatically from day one.

**Why this order:** the faculty's point is that a live system is the best test. P6 and P7 give a live address with real accounts about halfway through this plan, and from then on the rest is delivered as live updates. Moving to React (P8 and P9) is the largest piece of work; doing it after deployment means we never have a long period with nothing visible.

## 6. Decisions, with options and honest pros and cons

### D1. Frontend framework

| Option | Pros | Cons |
| --- | --- | --- |
| **Vite single page app** (recommended, already decided in ADR 0005) | Simple. Free static hosting with no card. Same React skills. No Server Components exposure | Home page needs a build step to be pre-rendered for search engines |
| Next.js | Server rendering built in. Many examples | A second server beside FastAPI. More to host and secure. More complex than this product needs today |
| Keep plain HTML | Nothing to rewrite | Not what the faculty asked for. Hard to maintain as screens grow, especially the ad editor |

### D2. Where the React pages are hosted

| Option | Pros | Cons |
| --- | --- | --- |
| **Cloudflare Pages** (recommended) | Free static requests and bandwidth, no card, 500 builds per month, preview deployments, free plan not limited to personal use | Server functions share a 100,000 requests per day limit (only matters if we use one as a proxy, see D5) |
| Vercel Hobby | Easy, good previews | The Hobby plan is for personal, non-commercial use only |
| Netlify Free | Easy | A hard stop: one project over its credits pauses every project on the account |
| GitHub Pages | Free | No server-side redirects, weaker for single page apps and previews |

### D3. Where the API runs

| Option | Pros | Cons |
| --- | --- | --- |
| **Render free web service** (fine for the first demos) | No card to start. Deploys from a Dockerfile or from GitHub. 750 instance hours per month | Sleeps after 15 minutes without traffic and takes about a minute to wake. 512 MB memory. Local files are wiped. Render's own documents advise against production use of free services |
| **Render paid, always on** | No sleeping. Same tools | A monthly cost. Earlier planning notes say about $7 to $25 per month, from memory and not checked against Render's price page |
| Fly.io (free plan returned 2026-11-23) | $5 of usage each month keeps a small app awake. Several regions | Needs a card. The plan is for personal accounts. Going over $5 bills the whole month. Newly changed, so less proven |
| Railway | Simple | After a 30 day trial the free plan is only $1 of credit per month, which is not enough for an always-on API |

Recommendation: start on **Render free** for the live address and the faculty, accept the one-minute first load (the page shows a "waking up" message), and move to a paid always-on instance, or Fly.io, when real users arrive. A GitHub Actions job that pings the API every 10 minutes could keep it awake (750 hours covers one service for a whole month), but it works against the host's intent and would not be relied on for real users.

### D4. Database

| Option | Pros | Cons |
| --- | --- | --- |
| **Neon free** (recommended) | PostgreSQL, 1 GB per project, 100 compute hours per month, no card, wakes in a few hundred milliseconds after idle, 10 branches (a copy of the database for testing a migration), 6 hour restore window | 5 GB egress per month. Plain database with no auth or storage extras (we do not need them). Commercial terms not confirmed, check before real customers |
| Supabase free | PostgreSQL plus auth and storage | 500 MB. The whole project **pauses after one week idle**, which is bad for demos. We already have our own sign-in, so the extras add little |
| Render PostgreSQL free | Same dashboard as the API | **Expires 30 days after creation**, then deleted. Not usable |
| Docker PostgreSQL on a rented server | Full control | We would run backups, updates and security ourselves. More work and cost |

Backups: Neon's 6 hour window is not a backup plan. P10 adds a daily dump to object storage.

### D5. How the sign-in cookie reaches the API

Our session cookie is `SameSite=Lax`. The free host names (`*.pages.dev` and `*.onrender.com`) are on different sites, so browsers treat the cookie as a third party cookie and may block it. This is the most important technical risk of going live.

| Option | Pros | Cons |
| --- | --- | --- |
| **Own domain with two subdomains**, `app.<domain>` and `api.<domain>` (recommended) | Same site, so the cookie works everywhere. A real address for the faculty | A domain costs roughly $10 to $15 per year (my estimate, not checked) |
| Pages proxy: the page host forwards `/api` to the API, so the browser sees one address | No domain needed. Same origin | A Cloudflare Pages Function counts against 100,000 requests per day. One more moving part. I have not tested this combination, so P6 starts with a short trial |
| Keep the two free host names | Free | Cookie may be blocked, especially in Safari. Not acceptable |

### D6. Where photos and exported ads are stored

| Option | Pros | Cons |
| --- | --- | --- |
| **Cloudflare R2** (S3 compatible) | Free allowance, no egress fees, same account as Pages | Its free limits are not checked yet. Check on the day |
| Supabase Storage | Simple | Ties us to a second vendor, and the project pauses when idle |
| Local disk | Nothing to set up | Wiped on every restart on a free host, so every photo would be lost |

### D7. How a change reaches production

| Option | Pros | Cons |
| --- | --- | --- |
| **Automatic on merge to `main`** (recommended for now) | Exactly what the faculty asked. Fast feedback. Only the owner and faculty use it today | A bad merge reaches the live site. Reduced by the checks, the smoke test after deploy, and the rollback step |
| Staging first, then production on a tag | Safer | Slower, and more to maintain for a project with no public users yet. Becomes goal P11 when real users arrive |

Migrations run automatically on deploy. Rule from now on: **a migration must work with the previous version of the code**, so adding a column is safe in one step and removing one takes two releases. CI proves each migration on PostgreSQL before merge.

### D8. Developer database without Docker

The owner moved to SQLite because Docker is awkward on their machine. Options once PostgreSQL is the default: (a) Docker Compose (the standard), (b) a free **Neon development branch** as the database, which needs only an internet connection, (c) SQLite as a clearly labelled fallback for the quickest start. Recommendation: (a) or (b) as the normal route, (c) kept so the faculty demo never depends on Docker.

## 7. Continuous integration and deployment, in plain words

**Today** (`.github/workflows/backend-ci.yml`) the checks run on every pull request:

1. `test`: lint (Ruff), type check (mypy, reports only), and the pytest suite.
2. `end-to-end`: starts the real API and pages, then runs the API smoke test, demo users twice, and browser tests (sign up, sign in, profile, sign out, admin).
3. `start-script`: runs the one-command start scripts on a fresh database.

**After this plan:**

| Workflow | Runs when | What it does |
| --- | --- | --- |
| `ci` (extended) | Every pull request | The current three jobs, now against a PostgreSQL service. New jobs: frontend lint, type check, unit tests, build; Playwright against the React build; Docker image builds |
| `deploy` | A merge to `main`, only after `ci` is green | 1. Run migrations on the production database. 2. Deploy the API container. 3. Build and publish the React app. 4. Smoke test the live address (health, sign in, one page). If step 4 fails, the run is marked failed and the previous version is redeployed |
| `preview` | A pull request touching the frontend | A temporary page address for that pull request, so the owner can see a change before merging |
| `backup` | Every night | Dumps the database to object storage and keeps the last 14 copies. A monthly restore test is on the checklist |
| `security` | Weekly, and Dependabot pull requests | `pip-audit`, `npm audit`, secret scanning |

Secrets (database URL, API keys, deploy tokens) live only in GitHub Actions secrets and the hosting dashboards, never in the repository.

## 8. Production-ready checklist (what "ready" means here)

| Area | Requirement | Goal |
| --- | --- | --- |
| Database | PostgreSQL, migrations only (no automatic table creation), daily backup and a tried restore | P3, P10 |
| Security | HTTPS only, `Secure` cookies, strict allowed origin, security headers, rate limits, no default or shared passwords, admin made on the server only | P4, P10 |
| Reliability | Health check, smoke test after deploy, one-step rollback, request ids in logs, error tracking | P4, P7, P10 |
| Quality | Pinned dependencies, strict TypeScript, tests for both halves, the browser tests run against the React build | P4, P8, P9 |
| Delivery | Protected `main`, every change a pull request, automatic deploy, preview pages | P2, P7 |
| Privacy | Notice that free AI providers may use submitted data, data export and deletion before public launch | before launch |
| Cost | Free until real users, with a written list of what to pay for first (always-on API, then OCR, then the language model) | [12-deployment-and-costs.md](12-deployment-and-costs.md) |

## 9. What I need from the owner

Decisions (each has a recommendation above):

1. D3: start the API on Render free, or do you have a card for Fly.io, or will you pay for an always-on instance now (price to be checked)?
2. D5: will you buy a domain (recommended), or should we try the proxy first?
3. D2, D4, D6: agree to Cloudflare Pages, Neon and R2?
4. D7: automatic deploy on every merge, as the faculty asked?
5. D8: Docker or a Neon development branch for your own computer?

Only you can do:

- Rename the default branch to `main` and turn on branch protection (P2).
- Create the accounts (Cloudflare, Neon, Render or Fly.io). I never need your passwords: you add tokens as GitHub secrets.
- Tell me whether Docker works on your machine.

## 10. Risks and honest limits

- **Free tiers are not production grade.** The API sleeps, the database has 1 GB, and limits change. This plan is "production style" (real database, real deployment, real checks) and not yet "always on for paying customers".
- **Moving to React is the largest piece.** Seven pages, the sign-in card, the Bangla and dark-mode behavior, and the admin console all have to be rebuilt and tested again. Bangla layout can only be judged on a real screen, so each page needs the owner's eyes.
- **Cookie plan is untested** until P6. It is the first thing to try.
- **Photos are lost until P5 is done.** Until then, uploads are switched off on the live site or clearly marked as temporary.
- **Auto-deploy can ship a bad change.** The mitigations are in D7, but they reduce the risk and do not remove it.
- **Terms of free plans** (commercial use on Neon and Render) were not confirmed. Check before real customers.
- **AI features** stay behind F8 and the plan in [25-ai-and-ad-engine-plan.md](25-ai-and-ad-engine-plan.md). The shut-down Gemini model name still has to be replaced once you have keys.

## Sources (checked 2026-11-25)

- React releases: [react.dev/blog](https://react.dev/blog) (React 19.3 on 2026-09-09, React Compiler v1.0, two Server Components security notices in December 2025)
- Vite: [Vite 8.1 announcement](https://vite.dev/blog/announcing-vite8-1)
- Free hosting limits (Render, Fly.io, Railway, Vercel, Netlify, Cloudflare), page checked 2026-09-16 with Fly.io updated 2026-11-23: [flaviocopes.com/hosting-free-tiers](https://flaviocopes.com/hosting-free-tiers/)
- Free PostgreSQL options, verified by the author on 2026-08-18: [freebase-cloud/free-postgres-hosting](https://github.com/freebase-cloud/free-postgres-hosting)
- Neon free plan: [Neon FAQ](https://neon.com/faqs/managed-postgres-databases-free-tier)
- Neon and Supabase compared (written by a competing vendor, so treat the framing with care): [layerbase.com](https://layerbase.com/blog/neon-vs-supabase)
