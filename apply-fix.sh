#!/usr/bin/env bash
# Run once from the project folder:  ./apply-fix.sh        (or ./apply-fix.sh --sqlite for no Docker)
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
[ -f Makefile ] && [ -d backend ] || { echo "Run this inside the adbanao project folder."; exit 1; }
chmod +x start-adbanao.sh stop-adbanao.sh
if [ ! -x .venv/bin/python ]; then
  echo "Creating the virtual environment..."; python3 -m venv .venv || exit 1
fi
.venv/bin/python -m pip install -q -r backend/requirements.txt || exit 1
.venv/bin/python scripts/fix_env.py "$@" || exit 1
.venv/bin/python scripts/fix_frontend.py
grep -q '^start:' Makefile || printf '\nstart:  ## One command: fix ports, migrate, set admin, run everything\n\t./start-adbanao.sh\n\nstop:  ## Free ports 8000 and 5173\n\t./stop-adbanao.sh\n' >> Makefile
echo; echo "Done. Now run:  ./start-adbanao.sh"
