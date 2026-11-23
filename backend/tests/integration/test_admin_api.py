import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")
pytest.importorskip("pydantic_settings")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PW = "blue-River-42"
ADMIN_EMAIL = "boss@example.com"
ADMIN_SECRET = "boss-secret-1"
SECOND_EMAIL = "second.boss@example.com"
SECOND_SECRET = "second-secret-1"


def _client():
    return TestClient(app)


def _signup(c, email, name="Person", **extra):
    r = c.post("/auth/signup", json={"email": email, "password": PW, "display_name": name, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def _admin_login(c, email=ADMIN_EMAIL, secret=ADMIN_SECRET, password=PW):
    return c.post("/auth/admin-login", json={"email": email, "password": password, "secret_word": secret})


def _verified_admin(c, email=ADMIN_EMAIL, secret=ADMIN_SECRET, name="Boss"):
    """Sign up (the first time) and sign in on the admin page."""
    r = c.post("/auth/signup", json={"email": email, "password": PW, "display_name": name})
    assert r.status_code in (201, 409), r.text
    assert _admin_login(c, email, secret).status_code == 200
    return c


@pytest.fixture()
def admin():
    with _client() as c:
        yield _verified_admin(c)


@pytest.fixture()
def member():
    """A normal user with a brand and a product, so the counts have something to show."""
    with _client() as c:
        email = f"m{id(c)}@example.com"
        user = _signup(c, email, "Mina Member")
        b = c.post("/brands", json={"name": f"B{id(c)}"}).json()
        c.post("/products", json={"brand_id": b["id"], "name": "Thing", "price": "10"})
        c.user = user
        yield c


def test_admin_login_cannot_be_used_to_become_admin(member):
    r = member.post("/auth/admin-login", json={"email": member.user["email"], "password": PW, "secret_word": "guess-word-1"})
    assert r.status_code == 401
    assert member.get("/admin/overview").status_code == 403


def test_signed_out_gets_401_and_normal_user_gets_403(member):
    with _client() as anon:
        for path in ["/admin/overview", "/admin/users", "/admin/activity", "/admin/export/users.csv"]:
            assert anon.get(path).status_code == 401
    for path in ["/admin/overview", "/admin/users", "/admin/activity",
                 "/admin/export/users.csv", "/admin/export/activity.csv", "/admin/users/1"]:
        assert member.get(path).status_code == 403, path
    assert member.patch("/admin/users/1", json={"role": "admin"}).status_code == 403
    assert member.post("/admin/users/1/sign-out").status_code == 403


def test_admin_login_checks_all_three_things(admin):
    with _client() as c:
        wrong = [
            _admin_login(c, secret="not-the-word"),
            _admin_login(c, password="wrong-Pass-1"),
            _admin_login(c, email="nobody@example.com"),
        ]
        c.post("/auth/signup", json={"email": "plain@example.com", "password": PW, "display_name": "P"})
        wrong.append(_admin_login(c, email="plain@example.com", secret="whatever-word"))
        msgs = {r.json()["detail"] for r in wrong}
        assert [r.status_code for r in wrong] == [401, 401, 401, 401]
        assert msgs == {"Incorrect email, password or secret word."}  # same message for every failure
        assert c.get("/admin/overview").status_code == 403  # only a plain-user session exists
        ok = _admin_login(c)
        assert ok.status_code == 200 and ok.json()["role"] == "admin"
        assert "secret" not in ok.text.lower() and "hash" not in ok.text.lower()
        assert c.get("/admin/overview").status_code == 200


def test_secret_word_ignores_surrounding_spaces_but_not_case(admin):
    with _client() as c:
        assert _admin_login(c, secret="  boss-secret-1  ").status_code == 200
    with _client() as c:
        assert _admin_login(c, secret="BOSS-SECRET-1").status_code == 401


def test_normal_sign_in_is_not_enough_for_an_admin(admin):
    with _client() as c:
        assert c.post("/auth/login", json={"email": ADMIN_EMAIL, "password": PW}).status_code == 200
        assert c.get("/users/me").json()["role"] == "admin"
        for path in ["/admin/overview", "/admin/users", "/admin/activity", "/admin/export/users.csv"]:
            r = c.get(path)
            assert r.status_code == 403 and r.json()["detail"] == "Admin sign-in required.", path
        assert c.patch("/admin/users/1", json={"role": "user"}).status_code == 403
        assert _admin_login(c).status_code == 200
        assert c.get("/admin/overview").status_code == 200


def test_admin_without_a_secret_word_cannot_use_the_admin_area():
    with _client() as c:
        c.post("/auth/signup", json={"email": "nosecret@example.com", "password": PW, "display_name": "N"})
        assert c.get("/users/me").json()["role"] == "admin"  # listed without a word
        assert _admin_login(c, "nosecret@example.com", "anything-here").status_code == 401
        assert c.get("/admin/overview").status_code == 403


def test_failed_and_successful_admin_sign_ins_are_logged(admin):
    with _client() as c:
        _admin_login(c, secret="wrong-secret-9")
        _admin_login(c)
    ev = admin.get("/admin/activity?group=admin&per_page=100").json()["items"]
    types = [e["event_type"] for e in ev]
    assert "admin_login_failed" in types and "admin_login" in types
    assert "wrong-secret-9" not in str(ev)


def test_suspended_admin_cannot_sign_in_on_the_admin_page(admin):
    with _client() as second:
        _verified_admin(second, SECOND_EMAIL, SECOND_SECRET, "Second")
        second_id = second.get("/users/me").json()["id"]
        assert admin.patch(f"/admin/users/{second_id}", json={"is_active": False}).status_code == 200
        assert second.get("/admin/overview").status_code == 401  # sessions ended
    with _client() as c:
        assert _admin_login(c, SECOND_EMAIL, "wrong-secret-9").status_code == 401  # still no hint
        r = _admin_login(c, SECOND_EMAIL, SECOND_SECRET)
        assert r.status_code == 403 and "suspended" in r.json()["detail"]
    assert admin.patch(f"/admin/users/{second_id}", json={"is_active": True}).status_code == 200
    with _client() as c:
        assert _admin_login(c, SECOND_EMAIL, SECOND_SECRET).status_code == 200


def test_demoted_admin_loses_the_secret_word(admin):
    with _client() as second:
        _verified_admin(second, SECOND_EMAIL, SECOND_SECRET, "Second")
        second_id = second.get("/users/me").json()["id"]
        assert admin.patch(f"/admin/users/{second_id}", json={"role": "user"}).json()["role"] == "user"
        assert second.get("/admin/overview").status_code == 403
        assert admin.patch(f"/admin/users/{second_id}", json={"role": "admin"}).status_code == 200
    # promoted again, but the old word is gone until the server owner sets one
    detail = admin.get(f"/admin/users/{second_id}").json()
    assert detail["role"] == "admin" and detail["has_secret_word"] is False
    assert admin.patch(f"/admin/users/{second_id}", json={"role": "user"}).status_code == 200


def test_role_is_in_users_me(admin, member):
    assert admin.get("/users/me").json()["role"] == "admin"
    assert member.get("/users/me").json()["role"] == "user"


def test_user_cannot_make_themselves_admin(member):
    assert member.patch("/users/me", json={"role": "admin", "is_active": True}).status_code == 200
    assert member.get("/users/me").json()["role"] == "user"
    assert member.get("/admin/overview").status_code == 403


def test_signup_cannot_choose_a_role():
    with _client() as c:
        r = c.post("/auth/signup", json={"email": "sneaky@example.com", "password": PW,
                                         "display_name": "S", "role": "admin"})
        assert r.status_code == 201 and r.json()["role"] == "user"


def test_overview_shape(admin, member):
    r = admin.get("/admin/overview?period=7d")
    assert r.status_code == 200
    body = r.json()
    assert len(body["signups_per_day"]) == 7 and len(body["active_per_day"]) == 7
    assert body["total_users"]["value"] >= 2
    assert body["new_signups"]["value"] >= 2
    assert body["ads_created"]["value"] == 0
    assert body["top_users"]
    assert admin.get("/admin/overview?period=today").json()["start"] == body["end"]


def test_overview_custom_range_validation(admin):
    assert admin.get("/admin/overview?period=custom").status_code == 422
    assert admin.get("/admin/overview?period=custom&start=2026-02-01&end=2026-01-01").status_code == 422
    assert admin.get("/admin/overview?period=custom&start=2026-01-01&end=2026-01-10").status_code == 200
    assert admin.get("/admin/overview?period=forever").status_code == 422


def test_users_list_search_filter_sort_paging(admin, member):
    r = admin.get("/admin/users?q=mina member").json()
    assert r["total"] >= 1 and r["items"][0]["display_name"] == "Mina Member"
    row = r["items"][0]
    assert row["brands"] == 1 and row["products"] == 1 and row["sign_ins"] == 0
    assert "password_hash" not in row
    assert admin.get("/admin/users?status=suspended&q=mina").json()["total"] == 0
    assert admin.get("/admin/users?role=admin").json()["total"] >= 1
    assert admin.get("/admin/users?q=%25").json()["total"] == 0  # % is not a wildcard
    for sort in ["joined", "last_active", "name", "email", "sign_ins", "brands", "products"]:
        for d in ["asc", "desc"]:
            assert admin.get(f"/admin/users?sort={sort}&direction={d}").status_code == 200
    assert admin.get("/admin/users?sort=password_hash").status_code == 422
    assert admin.get("/admin/users?per_page=1").json()["per_page"] == 1
    assert admin.get("/admin/users?per_page=1000").status_code == 422
    assert admin.get("/admin/users?page=0").status_code == 422


def test_user_detail_and_unknown_user(admin, member):
    uid = member.user["id"]
    d = admin.get(f"/admin/users/{uid}").json()
    assert d["email"] == member.user["email"] and "password_hash" not in d
    types = [e["event_type"] for e in d["recent_events"]]
    assert "signup" in types and "brand_created" in types and "product_created" in types
    assert admin.get("/admin/users/999999").status_code == 404


def test_actions_are_logged(admin, member):
    member.patch("/users/me", json={"phone": "01711000009"})
    member.post("/auth/logout")
    with _client() as c:
        c.post("/auth/login", json={"email": member.user["email"], "password": "wrong-Pass-1"})
        c.post("/auth/login", json={"email": member.user["email"], "password": PW})
    ev = admin.get(f"/admin/activity?user_id={member.user['id']}&per_page=100").json()["items"]
    types = {e["event_type"] for e in ev}
    assert {"signup", "profile_updated", "logout", "login_failed", "login"} <= types
    assert any(e["detail"] == "phone" for e in ev if e["event_type"] == "profile_updated")
    assert all(e["user"]["id"] == member.user["id"] for e in ev)


def test_failed_login_for_unknown_email_is_logged_without_the_email(admin):
    with _client() as c:
        c.post("/auth/login", json={"email": "nobody-here@example.com", "password": "whatever-1"})
    ev = admin.get("/admin/activity?event_type=login_failed&per_page=100").json()["items"]
    assert any(e["user"] is None for e in ev)
    assert "nobody-here" not in str(ev)


def test_activity_filters(admin, member):
    assert admin.get("/admin/activity?group=content").json()["items"]
    assert all(e["event_type"].startswith(("brand", "product"))
               for e in admin.get("/admin/activity?group=content&per_page=100").json()["items"])
    assert admin.get("/admin/activity?event_type=nonsense").status_code == 422
    assert admin.get("/admin/activity?period=today").status_code == 200
    assert admin.get("/admin/activity?period=custom").status_code == 422


def test_suspend_blocks_login_ends_sessions_and_can_be_undone(admin, member):
    uid = member.user["id"]
    assert member.get("/users/me").status_code == 200
    r = admin.patch(f"/admin/users/{uid}", json={"is_active": False})
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert member.get("/users/me").status_code == 401  # session was removed
    with _client() as c:
        wrong = c.post("/auth/login", json={"email": member.user["email"], "password": "wrong-Pass-1"})
        assert wrong.status_code == 401  # does not reveal the account is suspended
        blocked = c.post("/auth/login", json={"email": member.user["email"], "password": PW})
        assert blocked.status_code == 403 and "suspended" in blocked.json()["detail"]
    assert admin.patch(f"/admin/users/{uid}", json={"is_active": True}).json()["is_active"] is True
    with _client() as c:
        assert c.post("/auth/login", json={"email": member.user["email"], "password": PW}).status_code == 200
    types = {e["event_type"] for e in admin.get(f"/admin/activity?user_id={uid}&per_page=100").json()["items"]}
    assert {"admin_suspended", "admin_reactivated", "login_blocked"} <= types


def test_promote_and_demote(admin, member):
    uid = member.user["id"]
    assert admin.patch(f"/admin/users/{uid}", json={"role": "admin"}).json()["role"] == "admin"
    # a new admin has no secret word yet, so the admin area stays closed to them
    assert member.get("/admin/overview").status_code == 403
    assert admin.get(f"/admin/users/{uid}").json()["has_secret_word"] is False
    assert admin.patch(f"/admin/users/{uid}", json={"role": "user"}).json()["role"] == "user"
    assert member.get("/admin/overview").status_code == 403


def test_safeguards(admin):
    me = admin.get("/users/me").json()["id"]
    assert admin.patch(f"/admin/users/{me}", json={"is_active": False}).status_code == 409
    assert admin.patch(f"/admin/users/{me}", json={"role": "user"}).status_code == 409
    assert admin.patch(f"/admin/users/{me}", json={}).status_code == 422
    assert admin.patch("/admin/users/999999", json={"role": "admin"}).status_code == 404
    assert admin.patch(f"/admin/users/{me}", json={"role": "owner"}).status_code == 422


def test_sign_out_everywhere(admin, member):
    uid = member.user["id"]
    assert admin.post(f"/admin/users/{uid}/sign-out").status_code == 204
    assert member.get("/users/me").status_code == 401
    ev = admin.get(f"/admin/activity?event_type=admin_signed_out_user&user_id={uid}").json()["items"]
    assert ev and ev[0]["actor"]["email"] == ADMIN_EMAIL


def test_csv_exports(admin):
    with _client() as c:
        _signup(c, "csv-evil@example.com", "=HYPERLINK(\"http://x\")")
    r = admin.get("/admin/export/users.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    text = r.content.decode("utf-8-sig")
    assert text.splitlines()[0].startswith("id,name,email")
    assert "'=HYPERLINK" in text and ",=HYPERLINK" not in text
    assert "password" not in text.lower()
    a = admin.get("/admin/export/activity.csv?period=30d")
    assert a.status_code == 200 and "signup" in a.text
