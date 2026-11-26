#!/usr/bin/env python3
"""Open the real admin page in a browser. Needs the API on :8000 started with
ADMIN_EMAILS=admin@demo.adbanao.test=banao-demo-secret, the pages on :5173 and the demo users (seed_demo.py).

    python scripts/e2e_admin_page.py
"""

import sys

from playwright.sync_api import expect, sync_playwright

API, WEB, PW = "http://localhost:8000", "http://localhost:5173", "Demo-pass-123"


SECRET = "banao-demo-secret"


def login(ctx, email):
    r = ctx.request.post(f"{API}/api/v1/auth/login", data={"email": email, "password": PW})
    assert r.ok, f"login failed for {email}: {r.status}"


def admin_login(ctx):
    r = ctx.request.post(
        f"{API}/api/v1/auth/admin-login",
        data={"email": "admin@demo.adbanao.test", "password": PW, "secret_word": SECRET},
    )
    assert r.ok, f"admin sign-in failed: {r.status}"


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # signed out: sent to the sign-in page
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(f"{WEB}/admin.html")
        page.wait_for_url("**/admin-login.html", timeout=10000)
        print("PASS  signed-out visitor is sent to the admin sign-in page")
        ctx.close()

        # admin sign-in page: wrong secret word, then the right one
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(f"{WEB}/admin-login.html")
        page.fill("#email", "admin@demo.adbanao.test")
        page.fill("#pw", PW)
        page.fill("#secret", "wrong-secret-word")
        page.click("#go")
        expect(page.locator("#xForm")).to_contain_text("Incorrect", timeout=10000)
        assert "admin-login" in page.url
        print("PASS  wrong secret word is refused with one general message")
        page.fill("#secret", SECRET)
        page.click("#go")
        page.wait_for_url("**/admin.html", timeout=10000)
        expect(page.locator("#stats .stat")).to_have_count(5, timeout=10000)
        print("PASS  email + password + secret word opens the dashboard")
        page.click("#whoBtn")
        page.click("#signOutBtn")
        page.wait_for_url("**/admin-login.html", timeout=10000)
        print("PASS  admin sign out returns to the admin sign-in page")
        ctx.close()

        # an admin who signed in on the normal page only is sent to the admin sign-in
        ctx = browser.new_context()
        login(ctx, "admin@demo.adbanao.test")
        page = ctx.new_page()
        page.goto(f"{WEB}/admin.html")
        page.wait_for_url("**/admin-login.html", timeout=10000)
        print("PASS  normal sign-in is not enough: sent to the admin sign-in page")
        ctx.close()

        # normal user: sees Admins only
        ctx = browser.new_context()
        login(ctx, "rina@demo.adbanao.test")
        page = ctx.new_page()
        page.goto(f"{WEB}/admin.html")
        expect(page.locator("#denied")).to_be_visible(timeout=10000)
        expect(page.locator("#stats .stat")).to_have_count(0)
        print("PASS  normal user sees 'Admins only' and no data")
        ctx.close()

        # admin: dashboard, users, panel, theme, language, mobile
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        admin_login(ctx)
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"{WEB}/admin.html")
        expect(page.locator("#stats .stat")).to_have_count(5, timeout=10000)
        print("PASS  admin sees five summary cards")
        expect(page.locator("#usersBody tr").first).to_be_visible()
        page.fill("#q", "karim")
        expect(page.locator("#usersBody tr")).to_have_count(1, timeout=5000)
        print("PASS  user search works")
        page.locator("#usersBody tr").first.click()
        expect(page.locator("#panel")).to_be_visible()
        expect(page.locator("#pName")).to_contain_text("Karim")
        page.keyboard.press("Escape")
        expect(page.locator("#panel")).to_be_hidden()
        print("PASS  user panel opens and closes")
        page.click("#themeBtn")
        assert page.evaluate("document.documentElement.dataset.theme") == "dark"
        page.click("#langBtn")
        assert page.evaluate("document.documentElement.lang") == "bn"
        print("PASS  dark mode and Bangla switch")
        page.click("#tabActivity")
        expect(page.locator("#feed li").first).to_be_visible(timeout=5000)
        print("PASS  activity log shows events")
        page.set_viewport_size({"width": 390, "height": 844})
        page.click("#menuBtn")
        expect(page.locator("#side")).to_have_class("side open")
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "page scrolls sideways on mobile"
        print("PASS  mobile menu opens, no sideways scroll")
        assert not errors, errors
        browser.close()
    print("\nAll admin page checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
