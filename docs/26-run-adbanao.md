# AdBanao: how to run it

One script starts everything. No multiple terminals.

**Jump to:** [First time](#a-first-time-setup) · [Every day](#b-every-day-after-that) · [Links and logins](#links-and-logins) · [Common mistakes](#common-mistakes) · [Troubleshooting](#troubleshooting) · [Stop](#stop) · [Optional extras](#optional-extras)

> **Rule 1:** Always use `http://127.0.0.1:5173`. Never `localhost` or `0.0.0.0`.
> **Rule 2:** Run every command from inside the project folder (the one that contains `Makefile`, `backend` and `frontend`).

---

## A. First time setup

### 1. Install the requirements

| System | What you need |
| --- | --- |
| **Ubuntu / Linux** | Python 3 and venv: `sudo apt install python3 python3-venv` |
| **Windows** | Python 3 from python.org. Tick **"Add python.exe to PATH"** in the installer |

Docker is **not** needed. The app uses a local SQLite database by default.

### 2. Get the code

- **Clone:** `git clone -b step-01-repo-setup <repo-url> adbanao`
- **ZIP:** download from GitHub, then extract it.

Then go into the project folder (check with `ls` on Linux or `dir` on Windows).

### 3. Run the setup and start

**Ubuntu / Linux**
```bash
cd adbanao
chmod +x apply-fix.sh start-adbanao.sh stop-adbanao.sh
./apply-fix.sh
./start-adbanao.sh
```

**Windows (PowerShell, not Command Prompt)**
```powershell
cd adbanao
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\apply-fix.ps1
.\start-adbanao.ps1
```

`apply-fix` is the one-time setup: it creates the virtual environment, installs packages and fixes `.env`.
Wait for `AdBanao is running`, then open the links below.

---

## B. Every day after that

Open a terminal in the project folder and run one command:

| System | Command |
| --- | --- |
| **Ubuntu / Linux** | `./start-adbanao.sh` |
| **Windows** | `.\start-adbanao.ps1` |

Leave the terminal open. Press `Ctrl+C` to stop.

**After a `git pull`:** run the start script again. If `backend/requirements.txt` changed, run `apply-fix` once more first.

The start script does all of this for you: frees busy ports, checks the database, runs migrations, recreates the admin account, and starts the API and the pages.

---

## Links and logins

| What | Link |
| --- | --- |
| App and sign in | http://127.0.0.1:5173/ |
| Sign-up page | http://127.0.0.1:5173/#signup |
| Profile page | http://127.0.0.1:5173/profile.html |
| Admin sign-in | http://127.0.0.1:5173/admin-login.html |
| Admin dashboard | http://127.0.0.1:5173/admin.html |
| API test page | http://127.0.0.1:8000/docs |

**Admin login** (made for you the first time you start, and kept in `.env`, which is never committed):

The first start prints a new email, password and secret word. They are also saved in `.env` as
`ADBANAO_ADMIN_EMAIL`, `ADBANAO_ADMIN_PASSWORD` and `ADBANAO_ADMIN_SECRET`. Open `.env` any time to see them,
or change them there and start again. The admin page is http://127.0.0.1:5173/admin-login.html.

Never put a real password in a file that is committed: this repository is public. The start script refuses to
create the admin when `APP_ENV=production`.

**Normal users:** use **Create account** on the app with your own email and an 8+ character password.

---

## Common mistakes

### Both systems

| Mistake | Fix |
| --- | --- |
| Opening `localhost` or `0.0.0.0` | Use only `http://127.0.0.1:5173` |
| Trailing space or comma in the password or secret word | Click the eye icon and check the text. Type it by hand |
| Running the script from the wrong folder | `cd` into the project folder first |
| Skipping `apply-fix` on the first run | Run it once, then start |
| Closing the terminal and expecting the site to stay up | Closing it stops everything. Keep it open |
| Seeing an old page after an update | Use a private window or press `Ctrl+Shift+R` |

### Ubuntu / Linux only

| Mistake | Fix |
| --- | --- |
| `Permission denied` on `./apply-fix.sh` | ZIP downloads lose the executable flag. Run `chmod +x *.sh` or `bash apply-fix.sh` |
| `ensurepip is not available` or a venv error | `sudo apt install python3-venv` |

### Windows only

| Mistake | Fix |
| --- | --- |
| `Running scripts is disabled` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then try again |
| `python is not recognized` | Reinstall Python and tick **Add to PATH** |
| Using Command Prompt or Git Bash | Use PowerShell, or the VS Code terminal set to PowerShell |
| Scripts blocked after a ZIP download | In the project folder run `Get-ChildItem -Recurse \| Unblock-File` |
| Firewall or antivirus popup | Allow Python on private networks |

---

## Troubleshooting

| What you see | What to do |
| --- | --- |
| `Cannot reach the server` | Check the address bar starts with `http://127.0.0.1:5173` and the start script is still running |
| Admin sign-in says incorrect | Retype all three fields by hand, then run the start script again. It recreates the admin |
| Sign-in works but you land back on the login page | Use a private window (`Ctrl+Shift+P`) or `Ctrl+Shift+R` |
| Port busy | Nothing to do. The start script frees ports 8000 and 5173. Or run the stop script |
| `Run ./apply-fix.sh first` | Run the one-time setup from section A |
| `cannot reach the database` | Run `./apply-fix.sh --sqlite` (Windows: `.\apply-fix.ps1 -Sqlite`) |
| API will not start | Read `.run-logs/api.log` (Windows: `.run-logs\api.err`) and send the last lines |

---

## Stop

- Press `Ctrl+C` in the terminal running the start script.
- If something is stuck: `./stop-adbanao.sh` (Windows: `.\stop-adbanao.ps1`).

---

## Optional extras

**Demo users.** With the app running, open a **second** terminal in the project folder:

| System | Command |
| --- | --- |
| **Linux** | `source .venv/bin/activate && make seed` |
| **Windows** | `.venv\Scripts\Activate.ps1` then `python scripts\seed_demo.py` |

Sign in (not Create account) with password `Demo-pass-123`: `rina@demo.adbanao.test`, `karim@demo.adbanao.test`, `nusrat@demo.adbanao.test`.

**Several users at once.** One browser holds one signed-in user. Use a normal window, a private window, and a different browser.

**PostgreSQL with Docker (optional).** Set `DATABASE_URL=postgresql://adbanao:adbanao@localhost:5432/adbanao` in `.env`. The start script then starts the database container for you. Never use `docker compose down -v`, because it deletes the data.

**Database viewer (PostgreSQL only).** `ADMINER_PORT=8081 make db-viewer`, then open http://localhost:8081 with System `PostgreSQL`, Server `db`, Username `adbanao`, Password `adbanao`, Database `adbanao`.
