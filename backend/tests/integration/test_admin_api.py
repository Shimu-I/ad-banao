"""Admin routes: access control, numbers, user control, activity log, CSV."""

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")
pytest.importorskip("pydantic_settings")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.db.models import User  # noqa: E402
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

PW = "blue-River-42"


def _signup(name, **extra):
    c = TestClient(app)
    r = c.post("/auth/signup", json={"email": f"{name}@example.com", "password": PW, "display_name": name.title(), **extra})
    assert r.status_code == 201, r.text
    return c


def _make_admin(name):
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.email == f"{name}@example.com"))
        u.role = "admin"
        db.commit()


@pytest.fixture()
def world():
    Base.metadata.create_all(bind=engine)
    with TestClient(app):
        boss = _signup("boss")
        _make_admin("boss")
        alice, bob = _signup("alice"), _signup("bob")
        yield boss, alice, bob
        for c in (boss, alice, bob):
            c.close()
    Base.metadata.drop_all(bind=engine)


def _user_id(client, email):
    return next(u["id"] for u in client.get("/admin/users?limit=100").json()["items"] if u["email"] == email)


ADMIN_ROUTES = [
    ("get", "/admin/summary"),
    ("get", "/admin/users"),
    ("get", "/admin/users/1"),
    ("patch", "/admin/users/1"),
    ("post", "/admin/users/1/sign-out-everywhere"),
    ("get", "/admin/activity"),
    ("get", "/admin/export/users.csv"),
    ("get", "/admin/export/activity.csv"),
]


@pytest.mark.parametrize("method,path", ADMIN_ROUTES)
def test_admin_routes_refuse_anonymous_and_normal_users(world, method, path):
    _, alice, _ = world
    kwargs = {"json": {}} if method == "patch" else {}
    with TestClient(app) as anon:
        assert getattr(anon, method)(path, **kwargs).status_code == 401
    assert getattr(alice, method)(path, **kwargs).status_code == 403


def test_role_is_shown_on_own_profile(world):
    boss, alice, _ = world
    assert boss.get("/users/me").json()["role"] == "admin"
    assert alice.get("/users/me").json()["role"] == "user"


def test_summary_counts_and_days(world):
    boss, alice, bob = world
    alice.post("/auth/logout")
    alice.post("/auth/login", json={"email": "alice@example.com", "password": PW})
    alice.post("/auth/login", json={"email": "alice@example.com", "password": "wrong-pass-1"})
    bob.post("/brands", json={"name": "Bob Brand"})
    s = boss.get("/admin/summary").json()
    assert s["total_users"] == {"value": 3, "previous": 0}
    assert s["new_signups"]["value"] == 3
    assert s["sign_ins"]["value"] == 1
    assert s["active_users"]["value"] == 3
    assert s["ads_created"]["value"] == 0
    assert len(s["signups_per_day"]) == 7
    assert sum(p["value"] for p in s["signups_per_day"]) == 3
    assert s["signups_per_day"][-1]["value"] == 3  # all three signed up today
    assert s["active_per_day"][-1]["value"] == 3
    names = {t["display_name"] for t in s["top_users"]}
    assert {"Alice", "Bob"} <= names


def test_summary_range_rules(world):
    boss, _, _ = world
    assert boss.get("/admin/summary?start=2026-02-01&end=2026-01-01").status_code == 422
    assert boss.get("/admin/summary?start=2025-01-01&end=2026-01-01").status_code == 422
    one = boss.get("/admin/summary?start=2020-01-01&end=2020-01-01").json()
    assert one["new_signups"]["value"] == 0 and len(one["signups_per_day"]) == 1
    assert one["total_users"]["value"] == 0  # nobody existed in 2020


def test_user_list_search_filter_sort_page(world):
    boss, alice, bob = world
    alice.patch("/users/me", json={"language": "bn", "business_name": "Alice Pickles"})
    bob.post("/brands", json={"name": "Bob Brand"})
    data = boss.get("/admin/users").json()
    assert data["total"] == 3
    by_email = {u["email"]: u for u in data["items"]}
    assert by_email["bob@example.com"]["brands"] == 1
    assert by_email["alice@example.com"]["language"] == "bn"
    assert by_email["boss@example.com"]["role"] == "admin"
    assert by_email["alice@example.com"]["last_active"] is not None

    assert [u["email"] for u in boss.get("/admin/users?search=pickles").json()["items"]] == ["alice@example.com"]
    assert [u["email"] for u in boss.get("/admin/users?language=bn").json()["items"]] == ["alice@example.com"]
    assert boss.get("/admin/users?role=admin").json()["total"] == 1
    page = boss.get("/admin/users?limit=2&offset=2&sort=email&order=asc").json()
    assert page["total"] == 3 and [u["email"] for u in page["items"]] == ["boss@example.com"]
    assert boss.get("/admin/users?sort=password_hash").status_code == 422
    assert boss.get("/admin/users?status=weird").status_code == 422
    for sort in ("name", "email", "joined", "last_active", "sign_ins", "brands", "products", "status"):
        assert boss.get(f"/admin/users?sort={sort}").status_code == 200, sort


def test_user_list_never_exposes_secrets(world):
    boss, _, _ = world
    text = boss.get("/admin/users").text + boss.get("/admin/export/users.csv").text
    assert "scrypt" not in text and "password" not in text.lower().replace("password_changed", "")


def test_user_detail_has_recent_activity(world):
    boss, alice, _ = world
    alice.patch("/users/me", json={"phone": "017"})
    uid = _user_id(boss, "alice@example.com")
    d = boss.get(f"/admin/users/{uid}").json()
    assert d["user"]["email"] == "alice@example.com"
    assert [a["event"] for a in d["recent_activity"]][:2] == ["profile_updated", "signed_up"]
    assert boss.get("/admin/users/9999").status_code == 404


def test_suspend_blocks_and_signs_out_then_reactivate(world):
    boss, alice, _ = world
    uid = _user_id(boss, "alice@example.com")
    assert alice.get("/users/me").status_code == 200
    r = boss.patch(f"/admin/users/{uid}", json={"is_active": False})
    assert r.status_code == 200 and r.json()["status"] == "suspended"
    assert alice.get("/users/me").status_code == 401  # sessions were removed
    login = alice.post("/auth/login", json={"email": "alice@example.com", "password": PW})
    assert login.status_code == 403 and "suspended" in login.json()["detail"]
    r = boss.patch(f"/admin/users/{uid}", json={"is_active": True})
    assert r.json()["status"] == "active"
    assert alice.post("/auth/login", json={"email": "alice@example.com", "password": PW}).status_code == 200
    events = [a["detail"] for a in boss.get("/admin/activity?event=admin_action").json()["items"]]
    assert any("suspended: alice@example.com" in d for d in events)
    assert any("activated: alice@example.com" in d for d in events)


def test_role_change_and_self_protection(world):
    boss, _, bob = world
    bid = _user_id(boss, "bob@example.com")
    boss_id = _user_id(boss, "boss@example.com")
    assert bob.get("/admin/summary").status_code == 403
    assert boss.patch(f"/admin/users/{bid}", json={"role": "admin"}).json()["role"] == "admin"
    assert bob.get("/admin/summary").status_code == 200
    assert boss.patch(f"/admin/users/{bid}", json={"role": "user"}).json()["role"] == "user"
    assert bob.get("/admin/summary").status_code == 403
    # an admin cannot lock themselves out
    assert boss.patch(f"/admin/users/{boss_id}", json={"is_active": False}).status_code == 400
    assert boss.patch(f"/admin/users/{boss_id}", json={"role": "user"}).status_code == 400
    assert boss.patch(f"/admin/users/{bid}", json={"role": "owner"}).status_code == 422


def test_sign_out_everywhere(world):
    boss, alice, _ = world
    uid = _user_id(boss, "alice@example.com")
    assert boss.post(f"/admin/users/{uid}/sign-out-everywhere").status_code == 204
    assert alice.get("/users/me").status_code == 401
    assert boss.post("/admin/users/9999/sign-out-everywhere").status_code == 404


def test_activity_log_filters_and_privacy(world):
    boss, alice, bob = world
    alice.post("/auth/login", json={"email": "alice@example.com", "password": "wrong-pass-1"})
    with TestClient(app) as stranger:  # a password typed into the email box must not be kept
        stranger.post("/auth/login", json={"email": "my-secret-pass-99", "password": "x"})
    bob.post("/brands", json={"name": "Bob Brand"})

    failed = boss.get("/admin/activity?result=failed").json()
    assert failed["total"] == 2
    assert all(i["event"] == "sign_in_failed" for i in failed["items"])
    owners = sorted((i["user"]["email"] if i["user"] else None) for i in failed["items"] if True)
    assert owners == [None, "alice@example.com"] or owners == ["alice@example.com", None]
    assert "my-secret-pass-99" not in boss.get("/admin/activity?limit=100").text

    uid = _user_id(boss, "bob@example.com")
    mine = boss.get(f"/admin/activity?user_id={uid}").json()
    assert {i["event"] for i in mine["items"]} == {"signed_up", "brand_created"}
    assert boss.get("/admin/activity?event=brand_created").json()["total"] == 1
    assert boss.get("/admin/activity?limit=2").json()["items"].__len__() == 2
    assert boss.get("/admin/activity?event=DROP TABLE").status_code == 422
    assert boss.get("/admin/activity?start=2020-01-01&end=2020-01-02").json()["total"] == 0


def test_csv_downloads_and_formula_injection(world):
    boss, alice, _ = world
    alice.patch("/users/me", json={"display_name": '=HYPERLINK("http://evil","x")'})
    r = boss.get("/admin/export/users.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    assert r.text.splitlines()[0].startswith("id,name,email")
    assert "'=HYPERLINK" in r.text and ",=HYPERLINK" not in r.text
    a = boss.get("/admin/export/activity.csv")
    assert a.status_code == 200 and a.text.splitlines()[0] == "time_utc,user,email,event,result,detail"
    assert "signed_up" in a.text


def test_signup_email_in_admin_emails_becomes_admin_outside_production(monkeypatch):
    from app.api.v1 import auth as auth_module
    from app.core.config import Settings

    Base.metadata.create_all(bind=engine)
    try:
        monkeypatch.setattr(auth_module, "get_settings", lambda: Settings(admin_emails="Owner@Example.com", app_env="test"))
        with TestClient(app) as c:
            c.post("/auth/signup", json={"email": "owner@example.com", "password": PW, "display_name": "Owner"})
            assert c.get("/users/me").json()["role"] == "admin"
        monkeypatch.setattr(auth_module, "get_settings", lambda: Settings(admin_emails="owner2@example.com", app_env="production"))
        with TestClient(app) as c:
            c.post("/auth/signup", json={"email": "owner2@example.com", "password": PW, "display_name": "Owner2"})
            assert c.get("/users/me").json()["role"] == "user"  # never in production
    finally:
        Base.metadata.drop_all(bind=engine)
