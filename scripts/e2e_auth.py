#!/usr/bin/env python3
"""Browser test of the real sign-up, sign-in, profile and sign-out path.

Needs the API on :8000 and the pages on :5173 (see docs/20-test-on-your-pc.md), and Playwright:
    pip install playwright && playwright install chromium
    python scripts/e2e_auth.py
"""

import sys
import time

from playwright.sync_api import sync_playwright

WEB = "http://localhost:5173"
email = f"e2e{int(time.time())}@example.com"
password = "blue-River-42"
failures: list[str] = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"   -> {detail}"))
    if not ok:
        failures.append(name)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.goto(f"{WEB}/index.html#signup", wait_until="domcontentloaded")
    auth = page.frame_locator("#authFrame")

    # wrong things first
    auth.locator("#e2").fill("not-an-email")
    auth.locator("#p2").fill("short")
    auth.locator("#fup button[type=submit]").click()
    check("bad email is explained on the form", bool(auth.locator("#x2").text_content()))

    # real sign up
    auth.locator("#e2").fill(email)
    auth.locator("#p2").fill(password)
    auth.locator("#t2").check()
    auth.locator("#fup button[type=submit]").click()
    # After sign-up the home page leaves the form and shows the avatar badge.
    page.wait_for_selector("#avatarWrap.on", timeout=10000)
    check("sign up lands on the home page signed in", True)

    # duplicate
    # The home page leaves the sign-up screen when someone is already signed in,
    # so sign out first and only then open the sign-up screen again.
    page.goto(f"{WEB}/index.html", wait_until="domcontentloaded")
    page.evaluate("fetch('http://localhost:8000/api/v1/auth/logout',{method:'POST',credentials:'include'})")
    page.goto(f"{WEB}/index.html#signup", wait_until="domcontentloaded")
    page.reload()
    page.wait_for_load_state("networkidle")  # let the sign-in frame finish loading before typing into it
    auth = page.frame_locator("#authFrame")
    auth.locator("#e2").fill(email)
    auth.locator("#p2").fill(password)
    auth.locator("#t2").check()
    auth.locator("#fup button[type=submit]").click()
    msg = ""
    for i in range(40):  # wait up to 10 seconds for the answer instead of a fixed pause
        page.wait_for_timeout(250)
        msg = (auth.locator("#x2").text_content() or "") + (auth.locator("#z2").text_content() or "")
        if "already exists" in msg:
            break
        if i == 19 and not msg:  # one CI run saw no request at all; press the button once more, like a user would
            auth.locator("#fup button[type=submit]").click()
    check("duplicate email is refused with a message", "already exists" in msg, msg)

    # sign in with a wrong and then the right password
    page.goto(f"{WEB}/index.html#signin", wait_until="domcontentloaded")
    auth = page.frame_locator("#authFrame")
    auth.locator("#e1").fill(email)
    auth.locator("#p1").fill("wrong-pass-1")
    auth.locator("#fin button[type=submit]").click()
    page.wait_for_timeout(1500)
    check("wrong password message", "Incorrect" in (auth.locator("#y1").text_content() or ""))
    auth.locator("#p1").fill(password)
    auth.locator("#fin button[type=submit]").click()
    page.wait_for_selector("#avatarWrap.on", timeout=10000)
    check("sign in lands on the home page signed in", True)

    # header changes, profile page works
    page.goto(f"{WEB}/index.html", wait_until="domcontentloaded")
    page.wait_for_selector('#avatarWrap.on', timeout=10000)
    check("header shows the avatar badge when signed in", True)
    page.goto(f"{WEB}/profile.html", wait_until="domcontentloaded")
    page.wait_for_function("document.getElementById('who').textContent.includes('@')", timeout=10000)
    page.fill("#biz", "E2E Shop")
    page.fill("#phone", "01711111111")
    page.click("#saveBtn")
    page.wait_for_selector("#profile-msg.ok", timeout=10000)
    page.reload()
    page.wait_for_function("document.getElementById('biz').value !== ''", timeout=10000)
    check("profile changes survive a reload (read back from the database)",
          page.input_value("#biz") == "E2E Shop" and page.input_value("#phone") == "01711111111")

    # sign out
    page.click("#avatarBtn")  # the Sign out button lives inside the avatar menu
    page.click("#logout")
    page.wait_for_url("**/index.html#signin", timeout=10000)
    page.goto(f"{WEB}/profile.html", wait_until="domcontentloaded")
    page.wait_for_url("**/index.html#signin", timeout=10000)
    check("profile page is closed after sign out", True)
    browser.close()

print(f"\n{len(failures)} failed")
sys.exit(1 if failures else 0)
