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
    {"email": "rina@demo.adbanao.test", "display_name": "Rina Akter", "business_name": "Rina's Pickles", "phone": "01711000001", "language": "bn",
     "brand": "Rina's Pickles", "product": {"name": "Mango Pickle 500g", "price": "৳350", "unit": "500g", "key_features": ["Homemade", "No preservatives"]}},
    {"email": "karim@demo.adbanao.test", "display_name": "Karim Hossain", "business_name": "Karim Fashion House", "phone": "01711000002", "language": "en",
     "brand": "Karim Fashion House", "product": {"name": "Classic Panjabi", "price": "৳1,299", "key_features": ["Premium cotton", "Regular fit"]}},
    {"email": "nusrat@demo.adbanao.test", "display_name": "Nusrat Jahan", "business_name": "Nusrat Beauty Corner", "phone": "01711000003", "language": "en",
     "brand": "Nusrat Beauty Corner", "product": {"name": "Rose Face Lotion", "price": "৳650", "unit": "200ml", "key_features": ["Light on skin", "Rose scent"]}},
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
    status, body = call(opener, "POST", "/api/v1/auth/signup", {"email": u["email"], "password": PASSWORD, "display_name": u["display_name"]})
    created = status == 201
    if not created:
        status, body = call(opener, "POST", "/api/v1/auth/login", {"email": u["email"], "password": PASSWORD})
        if status != 200:
            sys.exit(f"Cannot sign in as {u['email']} ({status} {body}). Delete that user or reset the database.")
    status, body = call(opener, "PATCH", "/api/v1/users/me", {k: u[k] for k in ("business_name", "phone", "language")})
    if status != 200:
        sys.exit(f"Profile update failed for {u['email']}: {status} {body}")
    # one brand and one product each, so ownership can be shown
    status, brands = call(opener, "GET", "/api/v1/brands")
    brand = next((b for b in brands if b["name"] == u["brand"]), None) if status == 200 else None
    if brand is None:
        status, brand = call(opener, "POST", "/api/v1/brands", {"name": u["brand"]})
        if status != 201:
            sys.exit(f"Brand failed for {u['email']}: {status} {brand}")
    status, products = call(opener, "GET", f"/api/v1/products?brand_id={brand['id']}")
    if status == 200 and not any(p["name"] == u["product"]["name"] for p in products):
        status, body = call(opener, "POST", "/api/v1/products", {"brand_id": brand["id"], **u["product"]})
        if status != 201:
            sys.exit(f"Product failed for {u['email']}: {status} {body}")
    print(("created " if created else "updated ") + u["email"] + f"  (brand: {u['brand']}, product: {u['product']['name']})")

# An admin demo user. It becomes an admin when the API was started with
# ADMIN_EMAILS=admin@demo.adbanao.test=banao-demo-secret (development only), or after: make admin EMAIL=admin@demo.adbanao.test
ADMIN = {"email": "admin@demo.adbanao.test", "display_name": "Demo Admin"}
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
status, me = call(opener, "POST", "/api/v1/auth/signup", {"email": ADMIN["email"], "password": PASSWORD, "display_name": ADMIN["display_name"]})
if status != 201:
    status, me = call(opener, "POST", "/api/v1/auth/login", {"email": ADMIN["email"], "password": PASSWORD})
    if status != 200:
        sys.exit(f"Cannot sign in as {ADMIN['email']} ({status} {me}).")
role = me.get("role") if isinstance(me, dict) else None
print(f"{'ready  ' if role == 'admin' else 'created'} {ADMIN['email']}  (role: {role})")
if role != "admin":
    print("  Not an admin yet. Start the API with ADMIN_EMAILS=admin@demo.adbanao.test=banao-demo-secret, or run: make admin EMAIL=admin@demo.adbanao.test")

print(f"\nDemo password for all demo users: {PASSWORD}")
print("Demo admin secret word: banao-demo-secret")
