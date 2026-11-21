import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")
pytest.importorskip("pydantic_settings")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

GOOD = {"email": "Rina@Example.com", "password": "blue-River-42", "display_name": "Rina"}


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _signup(client, **over):
    return client.post("/auth/signup", json={**GOOD, **over})


def test_signup_signs_in_and_normalizes_email(client):
    r = _signup(client, email="new1@example.com")
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "new1@example.com"
    assert "password" not in body and "password_hash" not in body
    me = client.get("/users/me")
    assert me.status_code == 200 and me.json()["display_name"] == "Rina"
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie


def test_duplicate_email_conflict_ignores_case(client):
    assert _signup(client, email="dup@example.com").status_code == 201
    r = _signup(client, email="DUP@example.com")
    assert r.status_code == 409


@pytest.mark.parametrize(
    "over",
    [
        {"email": "nope"},
        {"password": "short"},
        {"password": "12345678"},
        {"display_name": "   "},
    ],
)
def test_signup_validation(client, over):
    assert _signup(client, **{"email": "v@example.com", **over}).status_code == 422


def test_login_logout_cycle(client):
    _signup(client, email="cycle@example.com")
    client.post("/auth/logout")
    assert client.get("/users/me").status_code == 401

    bad = client.post("/auth/login", json={"email": "cycle@example.com", "password": "wrong-pass-1"})
    assert bad.status_code == 401
    unknown = client.post("/auth/login", json={"email": "ghost@example.com", "password": "x"})
    assert unknown.status_code == 401
    assert bad.json() == unknown.json()  # does not reveal which emails exist

    ok = client.post("/auth/login", json={"email": " CYCLE@example.com", "password": GOOD["password"]})
    assert ok.status_code == 200
    assert client.get("/users/me").status_code == 200
    assert client.post("/auth/logout").status_code == 204
    assert client.get("/users/me").status_code == 401


def test_logout_requires_sign_in(client):
    assert client.post("/auth/logout").status_code == 401


def test_old_token_stops_working_after_logout(client):
    _signup(client, email="tok@example.com")
    token = client.cookies.get("adbanao_session")
    client.post("/auth/logout")
    client.cookies.set("adbanao_session", token)
    assert client.get("/users/me").status_code == 401


def test_profile_update_persists_in_database(client):
    _signup(client, email="prof@example.com")
    r = client.patch(
        "/users/me",
        json={"display_name": "Rina Akter", "business_name": "Rina's Pickles", "phone": "01700000000", "language": "bn"},
    )
    assert r.status_code == 200
    # a fresh sign-in (new session, new request) reads the stored values back
    client.post("/auth/logout")
    client.post("/auth/login", json={"email": "prof@example.com", "password": GOOD["password"]})
    me = client.get("/users/me").json()
    assert me["display_name"] == "Rina Akter"
    assert me["business_name"] == "Rina's Pickles"
    assert me["phone"] == "01700000000"
    assert me["language"] == "bn"


def test_profile_partial_update_and_clear(client):
    _signup(client, email="part@example.com", business_name="Shop")
    client.patch("/users/me", json={"phone": "123"})
    me = client.get("/users/me").json()
    assert me["business_name"] == "Shop" and me["phone"] == "123"
    client.patch("/users/me", json={"phone": None})
    assert client.get("/users/me").json()["phone"] is None


def test_profile_rejects_bad_values(client):
    _signup(client, email="bad@example.com")
    assert client.patch("/users/me", json={"language": "fr"}).status_code == 422
    assert client.patch("/users/me", json={"display_name": " "}).status_code == 422
    assert client.patch("/users/me", json={"email": "x@y.com"}).status_code == 200  # ignored field
    assert client.get("/users/me").json()["email"] == "bad@example.com"


def test_profile_needs_sign_in(client):
    client.cookies.clear()
    assert client.get("/users/me").status_code == 401
    assert client.patch("/users/me", json={"phone": "1"}).status_code == 401


def test_change_password(client):
    _signup(client, email="pw@example.com")
    assert client.post(
        "/users/me/password", json={"current_password": "wrong", "new_password": "fresh-Pass-77"}
    ).status_code == 400
    assert client.post(
        "/users/me/password", json={"current_password": GOOD["password"], "new_password": "fresh-Pass-77"}
    ).status_code == 204
    client.post("/auth/logout")
    assert client.post("/auth/login", json={"email": "pw@example.com", "password": GOOD["password"]}).status_code == 401
    assert client.post("/auth/login", json={"email": "pw@example.com", "password": "fresh-Pass-77"}).status_code == 200


def test_users_cannot_see_each_other(client):
    _signup(client, email="a1@example.com", display_name="A")
    client.post("/auth/logout")
    _signup(client, email="b1@example.com", display_name="B")
    assert client.get("/users/me").json()["display_name"] == "B"
