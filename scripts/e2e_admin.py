#!/usr/bin/env python3
"""Check the admin console against a running API.

    ADMIN_EMAILS=admin@demo.adbanao.test python -m uvicorn app.main:app --port 8000   (in backend/)
    python scripts/e2e_admin.py [http://localhost:8000]

Needs the API started in development mode with that ADMIN_EMAILS, and the demo users
(python scripts/seed_demo.py). Creates and suspends one throwaway user.
"""

import http.cookiejar
import json
import sys
import time
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
PW = "Demo-pass-123"
failures = []


def client():
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def call(op, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with op.open(req, timeout=20) as r:
            raw = r.read().decode()
            ctype = r.headers.get("content-type", "")
            return r.status, (json.loads(raw) if raw and "json" in ctype else raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw


def check(label, ok, extra=""):
    print(("PASS  " if ok else "FAIL  ") + label + ("" if ok else f"   {extra}"))
    if not ok:
        failures.append(label)


admin = client()
s, me = call(admin, "POST", "/auth/login", {"email": "admin@demo.adbanao.test", "password": PW})
if s != 200:
    sys.exit("Cannot sign in as admin@demo.adbanao.test. Run scripts/seed_demo.py first.")
check("admin user has the admin role", me["role"] == "admin",
      "Start the API with ADMIN_EMAILS=admin@demo.adbanao.test")

rina = client()
call(rina, "POST", "/auth/login", {"email": "rina@demo.adbanao.test", "password": PW})
check("normal user is refused (403)", call(rina, "GET", "/admin/overview")[0] == 403)
check("signed-out visitor is refused (401)", call(client(), "GET", "/admin/overview")[0] == 401)

s, ov = call(admin, "GET", "/admin/overview?period=30d")
check("overview loads with 30 days of points", s == 200 and len(ov["signups_per_day"]) == 30)
check("overview counts the demo users", s == 200 and ov["total_users"]["value"] >= 4)

s, users = call(admin, "GET", "/admin/users?q=demo.adbanao.test&per_page=100")
emails = {u["email"] for u in users["items"]} if s == 200 else set()
check("user list finds the demo users", {"rina@demo.adbanao.test", "karim@demo.adbanao.test"} <= emails)
check("demo users are flagged", s == 200 and all(u["is_demo"] for u in users["items"]))

victim = client()
email = f"e2e-{int(time.time())}@example.com"
s, v = call(victim, "POST", "/auth/signup", {"email": email, "password": PW, "display_name": "E2E Victim"})
check("throwaway user signs up", s == 201)
s, row = call(admin, "PATCH", f"/admin/users/{v['id']}", {"is_active": False})
check("admin suspends the user", s == 200 and row["is_active"] is False, row)
check("suspended user's session ends", call(victim, "GET", "/users/me")[0] == 401)
s, body = call(client(), "POST", "/auth/login", {"email": email, "password": PW})
check("suspended user cannot sign in (403)", s == 403, body)
s, row = call(admin, "PATCH", f"/admin/users/{v['id']}", {"is_active": True})
check("admin reactivates the user", s == 200 and row["is_active"] is True)
check("reactivated user can sign in", call(client(), "POST", "/auth/login", {"email": email, "password": PW})[0] == 200)

me_id = me["id"]
check("admin cannot suspend themselves", call(admin, "PATCH", f"/admin/users/{me_id}", {"is_active": False})[0] == 409)
s, ev = call(admin, "GET", f"/admin/activity?user_id={v['id']}&per_page=50")
types = {e["event_type"] for e in ev["items"]} if s == 200 else set()
check("activity log shows the suspension", {"signup", "admin_suspended", "admin_reactivated", "login_blocked"} <= types, types)

s, csv_text = call(admin, "GET", "/admin/export/users.csv")
check("users CSV downloads", s == 200 and csv_text.lstrip("﻿").startswith("id,name,email"))
s, csv_text = call(admin, "GET", "/admin/export/activity.csv?period=30d")
check("activity CSV downloads", s == 200 and "signup" in csv_text)

print()
if failures:
    sys.exit(f"{len(failures)} check(s) failed.")
print("All admin checks passed.")
