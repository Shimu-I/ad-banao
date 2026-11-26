#!/usr/bin/env bash
# One command to run AdBanao: frees busy ports, checks the database, migrates, fixes the admin,
# then starts the API and the pages. Press Ctrl+C to stop everything.
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
ROOT="$PWD"; PY="$ROOT/.venv/bin/python"; HOST=127.0.0.1
[ -x "$PY" ] || { echo "Run ./apply-fix.sh first."; exit 1; }
mkdir -p .run-logs

free_port() { "$PY" scripts/free_port.py "$@"; local rc=$?; sleep 1; return $rc; }
db_ok() { (cd backend && "$PY" -c "from app.db.session import engine; engine.connect().close()" >/dev/null 2>&1); }

free_port 8000 5173 || exit 1

if ! db_ok; then
  if grep -q '^DATABASE_URL=postgres' .env; then
    command -v docker >/dev/null || { echo "ERROR: PostgreSQL needs Docker, and Docker is not installed or not on the PATH. Install it, or use the no-Docker quick start: ./apply-fix.sh --sqlite"; exit 1; }
    echo "Starting the PostgreSQL container..."
    docker compose up -d db || { echo "ERROR: Docker could not start the database. Is Docker running? (Docker Desktop on Windows and Mac, 'sudo systemctl start docker' on Linux)"; exit 1; }
    for _ in $(seq 1 60); do db_ok && break; sleep 1; done
  fi
  db_ok || { echo "ERROR: cannot reach the database. Check the DATABASE_URL line in .env, or use the no-Docker quick start: ./apply-fix.sh --sqlite"; exit 1; }
fi

(cd backend && "$PY" -m alembic upgrade head >/dev/null) || { echo "ERROR: migration failed."; exit 1; }
"$PY" scripts/fix_frontend.py
"$PY" scripts/setup_admin.py || exit 1

(cd backend && exec "$PY" -m uvicorn app.main:app --host $HOST --port 8000 --reload >"$ROOT/.run-logs/api.log" 2>&1) &
API=$!
("$PY" scripts/serve_frontend.py 5173 $HOST >"$ROOT/.run-logs/web.log" 2>&1) &
WEB=$!
trap 'kill $API $WEB 2>/dev/null; free_port 8000 5173; echo Stopped.; exit 0' INT TERM

for _ in $(seq 1 30); do curl -fs "http://$HOST:8000/health" >/dev/null 2>&1 && break; sleep 1; done
curl -fs "http://$HOST:8000/health" >/dev/null 2>&1 || { echo "API did not start. See .run-logs/api.log"; kill $WEB $API 2>/dev/null; exit 1; }
cat <<MSG

AdBanao is running. Use ONLY these links (127.0.0.1, typed or clicked here):
  App:    http://$HOST:5173/
  Admin:  http://$HOST:5173/admin-login.html
  Email:  $("$PY" -c "import sys;sys.path.insert(0,'scripts');import _admin_creds as c;print(c.load()[0])")
  Password and secret word: in .env (ADBANAO_ADMIN_PASSWORD, ADBANAO_ADMIN_SECRET)
Logs: .run-logs/api.log and .run-logs/web.log      Stop: Ctrl+C
MSG
wait
