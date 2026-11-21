#!/usr/bin/env python3
"""Try the running API like a user would. Standard library only (Pillow is used for the test photo).

    python scripts/smoke_test.py http://localhost:8000

Prints one PASS or FAIL line per check and exits with 1 if anything failed.
"""

import http.cookiejar
import io
import json
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
results: list[tuple[bool, str]] = []


def call(method, path, body=None, raw=None, ctype=None):
    data, headers = None, {}
    if body is not None:
        data, headers = json.dumps(body).encode(), {"Content-Type": "application/json"}
    if raw is not None:
        data, headers = raw, {"Content-Type": ctype}
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with opener.open(req, timeout=20) as r:
            text = r.read().decode()
            return r.status, (json.loads(text) if text else None)
    except urllib.error.HTTPError as e:
        text = e.read().decode()
        try:
            return e.code, json.loads(text)
        except ValueError:
            return e.code, text


def check(name, ok, detail=""):
    results.append((ok, name))
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"   -> {detail}"))


def multipart(filename, content, ctype):
    b = uuid.uuid4().hex
    head = (
        f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {ctype}\r\n\r\n"
    ).encode()
    return head + content + f"\r\n--{b}--\r\n".encode(), f"multipart/form-data; boundary={b}"


def png_bytes(size):
    from PIL import Image  # installed with the backend requirements

    buf = io.BytesIO()
    Image.new("RGB", (size, size), (30, 90, 60)).save(buf, "PNG")
    return buf.getvalue()


def main():
    s, b = call("GET", "/health")
    check("server is up", s == 200, f"{s} {b}")
    if s != 200:
        return
    s, b = call("GET", "/health/db")
    check("server reaches the database", s == 200, f"{s} {b}")

    email = f"smoke{int(time.time())}@example.com"
    pw = "blue-River-42"
    s, b = call("POST", "/auth/signup", {"email": email, "password": pw, "display_name": "Smoke"})
    check("sign up", s == 201, f"{s} {b}")
    s, b = call("GET", "/users/me")
    check("signed in after sign up (cookie works)", s == 200 and b and b["email"] == email, f"{s} {b}")
    s, b = call("PATCH", "/users/me", {"business_name": "Smoke Shop", "phone": "01700000000", "language": "bn"})
    check("update profile", s == 200, f"{s} {b}")
    s, b = call("POST", "/auth/logout")
    check("sign out", s == 204, f"{s} {b}")
    s, _ = call("GET", "/users/me")
    check("profile is closed after sign out", s == 401, str(s))
    s, _ = call("POST", "/auth/login", {"email": email, "password": "wrong-pass-1"})
    check("wrong password is refused", s == 401, str(s))
    s, b = call("POST", "/auth/login", {"email": email, "password": pw})
    check("sign in", s == 200, f"{s} {b}")
    s, b = call("GET", "/users/me")
    ok = s == 200 and b["business_name"] == "Smoke Shop" and b["phone"] == "01700000000" and b["language"] == "bn"
    check("profile changes were saved in the database", ok, f"{s} {b}")

    s, brand = call("POST", "/brands", {"name": "Smoke Brand", "primary_colors": ["#1B4D34"]})
    check("create brand", s == 201, f"{s} {brand}")
    if s != 201:
        return
    s, p = call("POST", "/products", {"brand_id": brand["id"], "name": "Classic Panjabi", "price": "৳1,299", "unit": "0.5kg", "key_features": ["Premium cotton"]})
    check("create product", s == 201, f"{s} {p}")
    if s == 201:
        check("price ৳1,299 becomes 1299.00", p["price"] in ("1299.00", "1299"), p["price"])
        check("unit 0.5kg becomes 500 g", p["unit"] == "500 g", p["unit"])
        s, r = call("GET", f"/products/{p['id']}/readiness")
        check("readiness report", s == 200, f"{s} {r}")
        body, ct = multipart("shirt.png", png_bytes(900), "image/png")
        s, r = call("POST", f"/products/{p['id']}/image", raw=body, ctype=ct)
        check("upload a product photo", s in (200, 201), f"{s} {r}")
        body, ct = multipart("fake.png", b"%PDF-1.4 not an image", "image/png")
        s, r = call("POST", f"/products/{p['id']}/image", raw=body, ctype=ct)
        check("a PDF disguised as a photo is refused", 400 <= s < 500, f"{s} {r}")
    s, _ = call("POST", "/products", {"brand_id": brand["id"], "name": "X", "price": "12,99"})
    check("ambiguous price 12,99 is refused", s == 422, str(s))


try:
    main()
except Exception as exc:  # noqa: BLE001
    check("script ran without crashing", False, repr(exc))
failed = [n for ok, n in results if not ok]
print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
sys.exit(1 if failed else 0)
