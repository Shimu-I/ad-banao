#!/usr/bin/env python3
"""Create three demo users through the real API. Safe to run again (it signs in if they exist).

    python scripts/seed_demo.py [http://localhost:8000]

The password is for demos only. Never use it anywhere real.
"""

import http.cookiejar
import json
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
PASSWORD = "Demo-pass-123"
USERS = [
    {"email": "rina@demo.adbanao.test", "display_name": "Rina Akter", "business_name": "Rina's Pickles", "phone": "01711000001", "language": "bn"},
    {"email": "karim@demo.adbanao.test", "display_name": "Karim Hossain", "business_name": "Karim Fashion House", "phone": "01711000002", "language": "en"},
    {"email": "nusrat@demo.adbanao.test", "display_name": "Nusrat Jahan", "business_name": "Nusrat Beauty Corner", "phone": "01711000003", "language": "en"},
]


def call(opener, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with opener.open(req, timeout=20) as r:
            text = r.read().decode()
            return r.status, (json.loads(text) if text else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


for u in USERS:
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    status, body = call(opener, "POST", "/auth/signup", {"email": u["email"], "password": PASSWORD, "display_name": u["display_name"]})
    created = status == 201
    if not created:
        status, body = call(opener, "POST", "/auth/login", {"email": u["email"], "password": PASSWORD})
        if status != 200:
            sys.exit(f"Cannot sign in as {u['email']} ({status} {body}). Delete that user or reset the database.")
    status, body = call(opener, "PATCH", "/users/me", {k: u[k] for k in ("business_name", "phone", "language")})
    if status != 200:
        sys.exit(f"Profile update failed for {u['email']}: {status} {body}")
    print(("created " if created else "updated ") + u["email"])

print(f"\nDemo password for all three: {PASSWORD}")
