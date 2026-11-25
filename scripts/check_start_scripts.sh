#!/usr/bin/env bash
# Checks the one-command start on a fresh SQLite database, the way the owner uses it.
# Used by CI (job "start-script"); you can also run it on your PC from the project folder.
# It writes a new .env, so do not run it on a folder whose .env you want to keep.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
fail=0
ok()  { echo "PASS  $1"; }
bad() { echo "FAIL  $1"; fail=1; }
check() { if eval "$2" >/dev/null 2>&1; then ok "$1"; else bad "$1"; fi; }

rm -f .env adbanao.db
./apply-fix.sh --sqlite >/dev/null 2>&1; check "apply-fix.sh finishes" "[ -x .venv/bin/python ]"
check ".env uses SQLite" "grep -q '^DATABASE_URL=sqlite' .env"

./start-adbanao.sh > .run-logs-start.txt 2>&1 &
START=$!
for _ in $(seq 1 90); do curl -fs http://127.0.0.1:8000/health >/dev/null 2>&1 && break; sleep 1; done
check "API answers /health" "curl -fs http://127.0.0.1:8000/health"
check "pages are served" "curl -fs http://127.0.0.1:5173/ | grep -qi adbanao"
check "admin login was made and saved in .env" "grep -q '^ADBANAO_ADMIN_PASSWORD=.' .env"
check "the old published login is not in the repository" "! git grep -q 'admin-aa-bb-demo' -- ':!backend/tests/test_admin_creds.py' ':!scripts/check_start_scripts.sh'"

get() { grep "^$1=" .env | cut -d= -f2-; }
EMAIL=$(get ADBANAO_ADMIN_EMAIL); PW=$(get ADBANAO_ADMIN_PASSWORD); SECRET=$(get ADBANAO_ADMIN_SECRET)
login() {
  curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:8000/auth/admin-login \
    -H 'Content-Type: application/json' -d "{\"email\":\"$EMAIL\",\"password\":\"$PW\",\"secret_word\":\"$1\"}"
}
[ "$(login "$SECRET")" = 200 ] && ok "admin can sign in with the saved login" || bad "admin can sign in with the saved login"
[ "$(login wrong-secret-word)" = 401 ] && ok "a wrong secret word is refused" || bad "a wrong secret word is refused"

./stop-adbanao.sh >/dev/null 2>&1; sleep 2
kill "$START" 2>/dev/null
check "stop frees port 8000" "! curl -fs http://127.0.0.1:8000/health"
check "stop frees port 5173" "! curl -fs http://127.0.0.1:5173/"

# a program that is not AdBanao must be left alone
python3 -m http.server 5173 --bind 127.0.0.1 >/dev/null 2>&1 &
OTHER=$!; sleep 1
./start-adbanao.sh >/dev/null 2>&1; rc=$?
[ "$rc" != 0 ] && ok "start refuses when another program holds a port" || bad "start refuses when another program holds a port"
check "the other program is still running" "kill -0 $OTHER"
kill "$OTHER" 2>/dev/null

[ "$fail" = 0 ] && echo "ALL PASSED" || { echo "SOME FAILED"; cat .run-logs-start.txt .run-logs/api.log 2>/dev/null | tail -40; exit 1; }
