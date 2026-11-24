#!/usr/bin/env bash
# Usage: ./apply.sh [path-to-your-repo]   (default: current folder)
# Copies each fixed file to its original place. Your old versions are saved as *.bak.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "${1:-$(pwd)}" 2>/dev/null && pwd)" || { echo "Folder not found: ${1}"; exit 1; }
[ -d "$REPO/backend/app" ] && [ -d "$REPO/frontend" ] || { echo "Not the AdBanao repo folder: $REPO"; echo "Run: ./apply.sh /path/to/ad-banao"; exit 1; }
cd "$HERE/files"
find . -type f | while read -r f; do
  f="${f#./}"
  [ -f "$REPO/$f" ] && cp "$REPO/$f" "$REPO/$f.bak"
  mkdir -p "$REPO/$(dirname "$f")"
  cp "$f" "$REPO/$f"
  echo "updated  $f"
done
echo
echo "Done. Now:"
echo "  1) If your .env has DATABASE_URL=postgresql://user:password@... and you have no PostgreSQL, change it to sqlite:///./adbanao.db"
echo "  2) Restart the API:   make run"
echo "  3) Open the page as   http://localhost:5173/   (cd frontend && python3 -m http.server 5173)"
