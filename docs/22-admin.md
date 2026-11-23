# Admin console

The admin console is one page (`frontend/admin.html`) and a set of API routes under `/admin`. It shows how many people use AdBanao and what they do, and lets an admin suspend accounts, give or remove admin access and download CSV files. It has a light and a dark theme, a desktop layout (side menu) and a phone layout (slide-out menu, stacked cards), and English and Bangla.

## Who is an admin

Every user has a **role**: `user` (default) or `admin`. The role lives only in the database (`users.role`). No sign-up form, profile update or API field can set it.

| How | Where it works | Notes |
| --- | --- | --- |
| `ADMIN_EMAILS` in `.env` | Development and tests only | Comma-separated emails. The person becomes an admin the next time they sign up or sign in. **Ignored when `APP_ENV=production`** |
| `make admin EMAIL=someone@example.com` | Everywhere, including production | Runs `python -m app.cli make-admin`. The person must have signed up. Also `remove-admin` and `list-admins` |
| Another admin, from the Users panel | Everywhere | "Make admin" and "Remove admin" with a confirmation |

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

All routes need a signed-in active admin. Signed out: 401. Signed in but not an admin: 403.

| Route | Purpose |
| --- | --- |
| `GET /admin/overview?period=today\|7d\|30d\|custom&start=&end=` | Cards, chart series, top users |
| `GET /admin/users?q=&status=&role=&language=&sort=&direction=&page=&per_page=` | User list |
| `GET /admin/users/{id}` | One user with counts and the last 20 events |
| `PATCH /admin/users/{id}` body `{role?, is_active?}` | Change role or suspend/reactivate |
| `POST /admin/users/{id}/sign-out` | End all sessions |
| `GET /admin/activity?period=&group=&event_type=&user_id=&page=&per_page=` | Activity log |
| `GET /admin/export/users.csv`, `GET /admin/export/activity.csv` | Downloads |

`GET /users/me` now also returns `role`. Responses never include password hashes or session tokens.

## Database changes (migration 0003)

- `users.role` (string, default `user`) and `users.is_active` (boolean, default true).
- New table `activity_events`: `id`, `user_id` (who it is about, `SET NULL` if the user is removed), `actor_id` (the admin, when an admin did it), `event_type`, `detail` (short text, at most 300 characters), `created_at`. Indexed on user, type and time.
- Every existing user gets one `signup` event so the log is not empty. Downgrade removes both.

Events recorded: sign-up, sign-in, failed sign-in, blocked sign-in (suspended), sign-out, password change, profile update, brand and product create/update/archive/restore, and the admin actions. A failed sign-in for an email that does not exist is logged **without** the typed email.

## Safety details

- CSV cells that start with `=`, `+`, `-` or `@` get a leading apostrophe, so a user named `=HYPERLINK(...)` cannot run a formula in a spreadsheet.
- Search text is escaped, so `%` and `_` are not wildcards.
- The page builds all user text with `textContent`, never as HTML.
- Sorting uses a fixed list of columns; unknown names are rejected.

## Limits (honest list)

- Statistics are computed on request from the tables. That is fine for thousands of users; a large site would need summary tables.
- Days are UTC. For Bangladesh (UTC+6) "Today" starts at 06:00 local time.
- The activity log is never trimmed and failed sign-ins can fill it. There is no sign-in rate limit yet.
- Analytics and Settings in the menu are placeholders marked "Soon".
- Differences from the mockup: status is Active or Suspended (no "Pending", because accounts need no email check yet); the sidebar picture is a simple line drawing; the logo is the home page's "a." mark.

## Try it

```bash
echo "ADMIN_EMAILS=admin@demo.adbanao.test" >> .env     # development only
make run                                              # API
cd frontend && python3 -m http.server 5173            # pages
make seed                                             # demo users and the demo admin
```

Open http://localhost:5173/admin.html after signing in at the home page as `admin@demo.adbanao.test` (password `Demo-pass-123`). Automated checks: `python scripts/e2e_admin.py` (API) and `python scripts/e2e_admin_page.py` (browser). They also run in GitHub Actions and in `scripts/check_my_machine.sh`.
