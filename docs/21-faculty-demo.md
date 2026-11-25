# Faculty demo: pages talking to the database, with three users

A 7 to 10 minute demonstration that shows, live, that what users do on the pages changes real rows in the database. Everything here already works and was tested on the owner's machine (see [PROGRESS.md](PROGRESS.md)).

## What you will show

| Claim | How you prove it |
| --- | --- |
| Sign up writes to the database | Create a user on the page, refresh the `users` table, a new row appears |
| Passwords are not stored | The `password_hash` column shows an unreadable `scrypt$...` string, not the password |
| Signing in creates a session | A row appears in `user_sessions`. Sign out and the row disappears |
| Each user has their own data | Three users in three browsers each see only their own profile, brands and products. Another user's id answers "not found" |
| Profile edits are saved, not just shown | Edit a profile on the page, refresh Adminer, the row changed. Reload the page, the value is still there |
| Wrong password is refused | Try it. No session row is created |

## Setup (once, before the demo)

Pick one database. Both run the same app.

| | SQLite (default) | PostgreSQL (shows live tables) |
| --- | --- | --- |
| Needs Docker | No | Yes |
| Setup | `./start-adbanao.sh` | the steps in "Option B" below |
| Viewing the rows | the `sqlite3` command or the free app "DB Browser for SQLite" | the Adminer web page |

The demo script below says "Adminer" because that is the nicest way to show rows changing. With SQLite, show the same
thing with `sqlite3 adbanao.db "select id, email, display_name from users;"`.

### Option A: SQLite, no Docker (quickest)

Set up once with [26-run-adbanao.md](26-run-adbanao.md) (`./apply-fix.sh`), then:

```bash
cd adbanao && git pull
./start-adbanao.sh                 # terminal 1: migrates, starts the API and the pages (leave running)
make seed                          # terminal 2: creates the three demo users (needs `source .venv/bin/activate`)
```

The app is at http://127.0.0.1:5173/. Your own admin login is made on the first start and kept in `.env`.

### Option B: PostgreSQL with Docker

You need Docker and the project set up as in [20-test-on-your-pc.md](20-test-on-your-pc.md).

```bash
cd adbanao && source .venv/bin/activate
git pull
make db-viewer                     # PostgreSQL and the database viewer (Docker)
```

In `.env` make sure this line is present, so the app uses PostgreSQL:

```text
DATABASE_URL=postgresql://adbanao:adbanao@localhost:5432/adbanao
```

Then:

```bash
make migrate                       # create the tables
make run                           # terminal 1: the API (leave running)
cd frontend && python3 -m http.server 5173     # terminal 2: the pages (leave running)
make seed                          # terminal 3: creates the three demo users
```

The three demo users (the same password for all, for demos only):

| Name | Email | Business | Language |
| --- | --- | --- | --- |
| Rina Akter | `rina@demo.adbanao.test` | Rina's Pickles | Bangla |
| Karim Hossain | `karim@demo.adbanao.test` | Karim Fashion House | English |
| Nusrat Jahan | `nusrat@demo.adbanao.test` | Nusrat Beauty Corner | English |

Password for all three: `Demo-pass-123`

`make seed` can be run again at any time. It restores the three profiles to these values and gives each user one brand and one product of their own (Rina: Rina's Pickles, Mango Pickle 500g. Karim: Karim Fashion House, Classic Panjabi. Nusrat: Nusrat Beauty Corner, Rose Face Lotion).

### Open the database viewer (Option B)

Open http://localhost:8080 and sign in with (if the start failed with "port 8080 address already in use", run `docker compose down` and then `ADMINER_PORT=8081 make db-viewer`, and open http://localhost:8081 instead; `sudo ss -ltnp | grep 8080` shows what is using the port):

| Field | Value |
| --- | --- |
| System | PostgreSQL |
| Server | `db` |
| Username | `adbanao` |
| Password | `adbanao` |
| Database | `adbanao` |

Click **users** in the left list, then **Select data**. Keep this tab open next to the app.

### Prepare three separate browsers

Cookies are shared between tabs of the same browser, so one browser holds **one** signed-in user. For three users at once use three separate windows:

1. Normal Chrome or Firefox window: Rina
2. Private (incognito) window: Karim
3. A different browser, or a second private window of another browser: Nusrat

Open http://localhost:5173/ in each.

## The demo script

**1. Show the empty starting point (1 minute).**
In Adminer open `user_sessions`. It is empty. Open `users`: three rows, created by the seed script. Point at `password_hash`: "Not the password. A salted scrypt hash. Even with this table, nobody can sign in."

**2. Sign up a fourth user live (1 minute).**
In window 1 click Get Started, create an account with your own email and any password of 8 or more characters. The page says the account is ready. Switch to Adminer, refresh `users`: a new row. Refresh `user_sessions`: one new row. "The page just wrote to PostgreSQL."

**3. Three users sign in (2 minutes).**
In each of the three windows sign in as Rina, Karim and Nusrat. Refresh `user_sessions` in Adminer: one row per signed-in browser, each with a different `user_id`. Open Profile in each window: each shows a different name, business and phone. "Same page, same server, three people, three different sets of data."

**4. Edit and prove it is saved (2 minutes).**
In Rina's window open Profile, change the business name to something new, click Save changes. Show "Saved". Now go to Adminer, refresh `users`: Rina's row changed and `updated_at` moved. Back in Rina's window press reload: the value is still there. "Not a screen trick. It was read back from the database." Karim's and Nusrat's rows did not change.

**5. Wrong password and sign out (1 minute).**
In a private window try Karim's email with a wrong password: "Incorrect email or password". No new session row. Then in Karim's window click Sign out. Refresh `user_sessions`: his row is gone. Open the Profile page address in that window: it sends him back to sign in. "Signing out ends the session in the database, not only in the browser."

**5b. Show that each user owns their data (2 minutes). This is the strongest point.**
In Adminer open `brands`: three rows, each with a different `user_id`. Open `products`: three rows. Now in Rina's window (signed in) open http://localhost:8000/docs in a new tab. The page shares the sign-in cookie. Open `GET /brands`, click Try it out, Execute: only **Rina's Pickles** comes back. Do the same in Karim's window: only **Karim Fashion House**. Then in Karim's window try `GET /brands/{id}` with Rina's brand id (shown in Adminer): the answer is **404 Brand not found**. "The server answers not found, as if it did not exist, so ids reveal nothing." Try `GET /products` the same way.

**5c. Show the admin console (3 minutes).**
Open http://localhost:5173/admin-login.html and sign in with your admin login (the email, password and secret word saved in `.env` as `ADBANAO_ADMIN_*`; try a wrong secret word first: one general error). With Option B and `make run` you can instead put `ADMIN_EMAILS=admin@demo.adbanao.test=banao-demo-secret` in `.env`, restart the API and use `admin@demo.adbanao.test` with password `Demo-pass-123`.  Show the cards and charts, switch Dark and Bangla, and shrink the window to show the phone layout. Open the Users tab and click Karim: the panel shows his counts and recent activity. Click **Suspend account**, confirm, then in another window try to sign in as Karim with the right password: "This account has been suspended". In Adminer open `activity_events`: the suspension is a row with `actor_id` set to the admin. Reactivate him. Then in Rina's window open `/admin.html`: "Admins only". "Only the database role decides who is an admin, and no form can change it."

**6. (Optional) Show the browser side (1 minute).**
In Chrome press F12, open Application, then Cookies. The `adbanao_session` cookie is marked HttpOnly: page scripts cannot read it. The cookie holds a random token. The database holds only its hash.

**7. Show the proof of testing (1 minute).**
Show the green GitHub Actions run and `my-test-report.txt`: automated tests, a browser test of the same flow, and PostgreSQL checks all pass.

## Commands to use if the viewer is not available

```bash
docker compose exec db psql -U adbanao -d adbanao -c "select id, email, display_name, business_name, updated_at from users order by id;"
docker compose exec db psql -U adbanao -d adbanao -c "select id, user_id, created_at, expires_at from user_sessions;"
```

## Be honest about the limits

Say these before they ask:

- **The admin page works on real data, but the numbers are only as rich as the demo.** Ads are not built yet, so "Ads created" shows 0.
- **There are no screens for brands and products yet.** They are shown through the API page (`/docs`) and the database viewer. The screens come with goals U3 to U5.
- **No password reset or email check yet.** Planned.
- **The pages are a prototype** (plain HTML). The React version comes with goal U1.
- **Passwords for demo users are public.** They exist for the demo only. Delete them (or the database) before any real use.

## Reset after the demo

```bash
make seed                          # put the three profiles back
docker compose down -v             # Option B: remove the PostgreSQL data completely
rm adbanao.db                      # Option A: remove the SQLite file (stop the app first)
```
