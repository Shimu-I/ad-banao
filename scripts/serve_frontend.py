"""Serves the frontend folder with caching turned off, so the browser never uses an old copy.
    python scripts/serve_frontend.py [port] [host]"""
import functools
import http.server
import sys
from pathlib import Path

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5173
HOST = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"


class NoCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()


handler = functools.partial(NoCache, directory=str(Path(__file__).resolve().parents[1] / "frontend"))
http.server.ThreadingHTTPServer((HOST, PORT), handler).serve_forever()
