#!/usr/bin/env bash
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
.venv/bin/python scripts/free_port.py 8000 5173
echo Done.
