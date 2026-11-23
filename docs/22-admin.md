# Admin console

The admin console is one page (`frontend/admin.html`) and a set of API routes under `/admin`. It shows how many people use AdBanao and what they do, and lets an admin suspend accounts, give or remove admin access and download CSV files. It has a light and a dark theme, a desktop layout (side menu) and a phone layout (slide-out menu, stacked cards), and English and Bangla.

## How an admin signs in

Admins use their own page, `frontend/admin-login.html`, and give **three things**: admin email, password and a **secret word** (a second password that only admins have). A wrong email, password or secret word, a normal user, and an unknown email all get the same message, "Incorrect email, password or secret word." A suspended admin is told the account is suspended, but only when all three are right.

Only a sign-in on that page opens the admin area. An admin who signs in on the normal page is a normal user there, and `/admin/*` answers 403 "Admin sign-in required." (the admin page then sends them to the admin sign-in). The secret word is stored only as a scrypt hash (`users.admin_secret_hash`), is case sensitive, has 6 to 128 characters, and is set on the server, never from a web page. Lost word: the person who runs the server sets a new one with `make admin-secret EMAIL=...`.

## Who is an admin

Every user has a **role**: `user` (default) or `admin`. The role lives only in the database (`users.role`). No sign-up form, profile update or API field can set it.

| How | Where it works | Notes |
| --- | --- | --- |
| `ADMIN_EMAILS` in `.env` | Development and tests only | Comma-separated `email=secretword` entries, for example `admin@demo.adbanao.test=banao-demo-secret`. The person becomes an admin, with that secret word, the next time they sign up or sign in. **Ignored when `APP_ENV=production`** |
| `make admin EMAIL=someone@example.com` | Everywhere, including production | Runs `python -m app.cli make-admin`. Asks for the secret word (typing hidden, so it stays out of shell history). The person must have signed up. Also `set-secret`, `remove-admin` and `list-admins` |
| Another admin, from the Users panel | Everywhere | "Make admin" and "Remove admin" with a confirmation. A person made admin this way has **no secret word yet**, so they cannot open the admin area until the server owner runs `make admin EMAIL=...`. Removing admin access also deletes their secret word |

The first admin in production is always made with the command line, on the server, by whoever runs the server.

## What an admin can do

| Control | Effect |
| --- | --- |
| Suspend account | Sets `is_active = false`. The person's sign-in sessions are deleted at once. They cannot sign in again until reactivated (the page says the account is suspended, but only after a correct password, so it does not reveal which emails exist). Their data is kept |
| Reactivate account | They can sign in again |
| Make admin / Remove admin | Changes `users.role` |
| Sign out everywhere | Deletes all of the person's sessions |
| Download users (CSV) / Download activity (CSV) | Respects the current filters. Up to 50,000 rows |

Safeguards (tested): you cannot suspend or demote yourself, and the last active admin can never be suspended or demoted. Every control is written to the activity log with the admin's name.

## What the page shows

- **Period**: Today, 7 days, 30 days or a custom range. Days are **UTC days**. All cards compare with the previous period of the same length.
- **Five cards**: total users, new sign-ups, active users (people with at least one real action in the period; failed or blocked sign-ins do not count), sign-ins, ads created (always 0 until ads exist; shown as "coming soon").
- **Charts**: sign-ups per day (bars) and active users per day (line). Each has a Table view with the same numbers, and a tooltip on hover or focus.
- **Top users**: by sign-ins plus actions (brand, product, profile and password changes) in the period. Demo users carry a "Demo" tag.
- **Users tab**: search (name, email, business), filters (status, role, language), sort by any number column, 10 to 100 rows per page. Click a row for the side panel with facts, controls and recent activity.
- **Activity Log tab**: filter by group (sign-ins, brands and products, account changes, admin actions), by period or all time, and by one user.
- **Not an admin?** The page shows "Admins only" and loads no data. Signed-out visitors are sent to the sign-in page.

## API

All `/admin` routes need an active admin who signed in on the admin page. Signed out: 401. Not an admin: 403 "Admins only." Admin signed in on the normal page: 403 "Admin sign-in required."

| Route | Purpose |
| --- | --- |
| `POST /auth/admin-login` body `{email, password, secret_word}` | Admin sign-in (not under `/admin`; signed out is fine) |
| `GET /admin/overview?period=today\|7d\|30d\|custom&start=&end=` | Cards, chart series, top users |
| `GET /admin/users?q=&status=&role=&language=&sort=&direction=&page=&per_page=` | User list |
| `GET /admin/users/{id}` | One user with counts and the last 20 events |
| `PATCH /admin/users/{id}` body `{role?, is_active?}` | Change role or suspend/reactivate |
| `POST /admin/users/{id}/sign-out` | End all sessions |
| `GET /admin/activity?period=&group=&event_type=&user_id=&page=&per_page=` | Activity log |
| `GET /admin/export/users.csv`, `GET /admin/export/activity.csv` | Downloads |

`GET /users/me` also returns `role`. Responses never include password hashes or session tokens.

## Database changes (migration 0003)

- `users.role` (string, default `user`) and `users.is_active` (boolean, default true).
- New table `activity_events`: `id`, `user_id` (who it is about, `SET NULL` if the user is removed), `actor_id` (the admin, when an admin did it), `event_type`, `detail` (short text, at most 300 characters), `created_at`. Indexed on user, type and time.
- Every existing user gets one `signup` event so the log is not empty. Downgrade removes both.

Events recorded: sign-up, sign-in, failed sign-in, blocked sign-in (suspended), sign-out, password change, profile update, brand and product create/update/archive/restore, and the admin actions. A failed sign-in for an email that does not exist is logged **without** the typed email.

## Database changes (migration 0004)

- `users.admin_secret_hash` (nullable): hash of the secret word.
- `user_sessions.admin_verified` (boolean, default false): true only for sessions made on the admin sign-in page. Existing sessions become unverified, so admins sign in again on the admin page.
- New events `admin_login` and `admin_login_failed` (the failed one never stores what was typed).

## Safety details

- CSV cells that start with `=`, `+`, `-` or `@` get a leading apostrophe, so a user named `=HYPERLINK(...)` cannot run a formula in a spreadsheet.
- Search text is escaped, so `%` and `_` are not wildcards.
- The page builds all user text with `textContent`, never as HTML.
- Sorting uses a fixed list of columns; unknown names are rejected.

## Limits (honest list)

- Statistics are computed on request from the tables. That is fine for thousands of users; a large site would need summary tables.
- Days are UTC. For Bangladesh (UTC+6) "Today" starts at 06:00 local time.
- The activity log is never trimmed and failed sign-ins can fill it. There is **no limit on wrong guesses** for the password or secret word yet; failed admin sign-ins are logged so you can see an attack, but nothing blocks it. Add rate limiting before a public launch.
- There is no "forgot secret word" page by design; it is reset on the server.
- Analytics and Settings in the menu are placeholders marked "Soon".
- Differences from the mockup: status is Active or Suspended (no "Pending", because accounts need no email check yet); the sidebar picture is a simple line drawing; the logo is the home page's "a." mark.

## Try it

```bash
echo "ADMIN_EMAILS=admin@demo.adbanao.test=banao-demo-secret" >> .env     # development only
make run                                              # API
cd frontend && python3 -m http.server 5173            # pages
make seed                                             # demo users and the demo admin
```

Open http://localhost:5173/admin-login.html and sign in with email `admin@demo.adbanao.test`, password `Demo-pass-123` and secret word `banao-demo-secret`. You land on the dashboard. Automated checks: `python scripts/e2e_admin.py` (API) and `python scripts/e2e_admin_page.py` (browser). They also run in GitHub Actions and in `scripts/check_my_machine.sh`.
