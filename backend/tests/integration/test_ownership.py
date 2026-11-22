"""One user must never see or change another user's brands and products."""

import io

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")
pytest.importorskip("pydantic_settings")
pytest.importorskip("httpx")
try:
    import python_multipart  # noqa: F401
except ImportError:
    pytest.importorskip("multipart")

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.db.session import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


def _user(name):
    c = TestClient(app)
    r = c.post(
        "/auth/signup",
        json={"email": f"{name}@example.com", "password": "blue-River-42", "display_name": name},
    )
    assert r.status_code == 201, r.text
    return c


@pytest.fixture()
def people():
    Base.metadata.create_all(bind=engine)
    with TestClient(app):  # runs startup once
        rina, karim, nusrat = _user("rina"), _user("karim"), _user("nusrat")
        yield rina, karim, nusrat
        for c in (rina, karim, nusrat):
            c.close()
    Base.metadata.drop_all(bind=engine)


def _png():
    buf = io.BytesIO()
    Image.new("RGB", (800, 800), (10, 120, 60)).save(buf, "PNG")
    return buf.getvalue()


def _setup(client, brand="Pickles", product="Mango Pickle"):
    b = client.post("/brands", json={"name": brand}).json()
    p = client.post(
        "/products",
        json={"brand_id": b["id"], "name": product, "price": "250", "key_features": ["Homemade"]},
    ).json()
    return b, p


@pytest.mark.parametrize(
    "method,path",
    [("get", "/brands"), ("post", "/brands"), ("get", "/products"), ("post", "/products"),
     ("get", "/brands/1"), ("get", "/products/1/readiness")],
)
def test_everything_needs_sign_in(method, path):
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as anon:
        kwargs = {"json": {}} if method == "post" else {}
        assert getattr(anon, method)(path, **kwargs).status_code == 401
    Base.metadata.drop_all(bind=engine)


def test_lists_only_show_your_own_data(people):
    rina, karim, nusrat = people
    _setup(rina, "Rina Pickles", "Mango Pickle")
    _setup(karim, "Karim Fashion", "Classic Panjabi")
    assert [b["name"] for b in rina.get("/brands").json()] == ["Rina Pickles"]
    assert [b["name"] for b in karim.get("/brands").json()] == ["Karim Fashion"]
    assert nusrat.get("/brands").json() == []
    assert [p["name"] for p in rina.get("/products").json()] == ["Mango Pickle"]
    assert [p["name"] for p in karim.get("/products").json()] == ["Classic Panjabi"]
    assert nusrat.get("/products").json() == []


def test_other_users_brand_is_not_found(people):
    rina, karim, _ = people
    brand, _ = _setup(rina)
    bid = brand["id"]
    assert karim.get(f"/brands/{bid}").status_code == 404
    assert karim.patch(f"/brands/{bid}", json={"name": "Stolen"}).status_code == 404
    assert karim.post(f"/brands/{bid}/archive").status_code == 404
    assert karim.post(f"/brands/{bid}/restore").status_code == 404
    r = karim.post(f"/brands/{bid}/logo", files={"file": ("l.png", _png(), "image/png")})
    assert r.status_code == 404
    # the owner's brand is untouched
    assert rina.get(f"/brands/{bid}").json()["name"] == "Pickles"


def test_other_users_product_is_not_found(people):
    rina, karim, _ = people
    brand, product = _setup(rina)
    pid = product["id"]
    for method, path, kw in [
        ("get", f"/products/{pid}", {}),
        ("patch", f"/products/{pid}", {"json": {"name": "Stolen"}}),
        ("post", f"/products/{pid}/archive", {}),
        ("post", f"/products/{pid}/restore", {}),
        ("get", f"/products/{pid}/readiness", {}),
        ("post", f"/products/{pid}/generate-copy", {"json": {}}),
        ("post", f"/products/{pid}/image", {"files": {"file": ("p.png", _png(), "image/png")}}),
    ]:
        assert getattr(karim, method)(path, **kw).status_code == 404, f"{method} {path}"
    assert rina.get(f"/products/{pid}").json()["name"] == "Mango Pickle"


def test_cannot_add_a_product_to_someone_elses_brand(people):
    rina, karim, _ = people
    brand, _ = _setup(rina)
    r = karim.post("/products", json={"brand_id": brand["id"], "name": "Sneaky"})
    assert r.status_code == 404
    assert [p["name"] for p in rina.get("/products").json()] == ["Mango Pickle"]


def test_product_filter_by_foreign_brand_returns_nothing(people):
    rina, karim, _ = people
    brand, _ = _setup(rina)
    assert karim.get(f"/products?brand_id={brand['id']}").json() == []


def test_two_users_can_use_the_same_brand_name(people):
    rina, karim, _ = people
    assert rina.post("/brands", json={"name": "Fresh Foods"}).status_code == 201
    assert karim.post("/brands", json={"name": "Fresh Foods"}).status_code == 201
    assert rina.post("/brands", json={"name": "fresh foods"}).status_code == 409  # own duplicate


def test_signing_out_closes_brands_too(people):
    rina, _, _ = people
    _setup(rina)
    rina.post("/auth/logout")
    assert rina.get("/brands").status_code == 401
