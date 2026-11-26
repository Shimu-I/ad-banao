"""Request ids, one error format, readable logs and AI settings (goal F8)."""

import json
import logging

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")
pytest.importorskip("httpx")

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.logging import JsonFormatter, RequestIdFilter  # noqa: E402
from app.core.request_context import clean_request_id, request_id_var  # noqa: E402
from app.main import app, create_app  # noqa: E402
from app.providers.llm import GeminiProvider, GroqProvider, providers_from_settings  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_every_answer_has_a_request_id(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert len(r.headers["X-Request-ID"]) >= 8


def test_a_safe_id_from_the_caller_is_kept_and_an_unsafe_one_replaced(client):
    assert client.get("/health", headers={"X-Request-ID": "trace-abc-12345"}).headers["X-Request-ID"] == "trace-abc-12345"
    bad = client.get("/health", headers={"X-Request-ID": "x y\\n<script>"}).headers["X-Request-ID"]
    assert bad != "x y\\n<script>" and clean_request_id(bad) == bad


def test_not_found_uses_the_error_format(client):
    r = client.get("/nope")
    body = r.json()
    assert r.status_code == 404
    assert body["code"] == "not_found" and body["detail"] and body["request_id"] == r.headers["X-Request-ID"]


def test_signed_out_and_conflict_keep_their_detail_and_get_a_code(client):
    r = client.get("/users/me")
    assert r.status_code == 401 and r.json()["detail"] == "Not signed in" and r.json()["code"] == "not_signed_in"
    user = {"email": "found1@example.com", "password": "Correct-horse-9", "display_name": "Found"}
    assert client.post("/auth/signup", json=user).status_code == 201
    dup = client.post("/auth/signup", json=user)
    assert dup.status_code == 409 and dup.json()["code"] == "conflict" and "already exists" in dup.json()["detail"]


def test_validation_errors_are_listed_with_a_code(client):
    r = client.post("/auth/signup", json={"email": "not-an-email"})
    body = r.json()
    assert r.status_code == 422 and body["code"] == "validation_error"
    assert isinstance(body["detail"], list) and body["request_id"] == r.headers["X-Request-ID"]


def _app_with_test_routes():
    test_app = create_app()

    @test_app.get("/_named")
    def named():
        raise HTTPException(status_code=422, detail={"code": "not_an_image", "message": "x"})

    @test_app.get("/_boom")
    def boom():
        raise RuntimeError("secret internal detail")

    return test_app


def test_a_route_that_names_its_problem_keeps_that_code():
    with TestClient(_app_with_test_routes()) as c:
        r = c.get("/_named")
    assert r.json()["code"] == "not_an_image" and r.json()["detail"]["message"] == "x"


def test_unexpected_error_hides_the_cause_and_is_logged_with_the_id(caplog, monkeypatch):
    test_app = _app_with_test_routes()  # building the app sets up our logger, so change it afterwards
    monkeypatch.setattr(logging.getLogger("app"), "propagate", True)  # let caplog see our logger
    with TestClient(test_app, raise_server_exceptions=False) as c:
        with caplog.at_level(logging.ERROR, logger="app.errors"):
            r = c.get("/_boom")
    body = r.json()
    assert r.status_code == 500 and body["code"] == "internal_error"
    assert "secret internal detail" not in r.text
    assert r.headers["X-Request-ID"] == body["request_id"]
    assert any("unhandled error" in rec.getMessage() for rec in caplog.records)


def test_json_log_line_is_valid_json_with_the_request_id():
    token = request_id_var.set("req-123456")
    try:
        record = logging.LogRecord("app.access", logging.INFO, "f", 1, "GET %s -> %s", ("/health", 200), None)
        record.status = 200
        RequestIdFilter().filter(record)
        data = json.loads(JsonFormatter().format(record))
    finally:
        request_id_var.reset(token)
    assert data["request_id"] == "req-123456" and data["status"] == 200 and data["message"] == "GET /health -> 200"


class _Settings:
    def __init__(self, gemini="", groq=""):
        self.gemini_api_key, self.groq_api_key = gemini, groq
        self.gemini_model, self.groq_model = "gemini-test-model", "groq-test-model"


def test_model_names_come_from_settings():
    found = providers_from_settings(_Settings("g-key", "q-key"))
    assert [type(p) for p in found] == [GeminiProvider, GroqProvider]
    assert [p.model for p in found] == ["gemini-test-model", "groq-test-model"]
    assert providers_from_settings(_Settings()) == []


def test_provider_health_lists_models_but_never_keys(client, monkeypatch):
    monkeypatch.setattr("app.api.v1.health.get_settings", lambda: _Settings("SECRET-GEMINI-KEY"))
    r = client.get("/health/providers")
    assert r.status_code == 200
    assert r.json()["configured"] == [{"name": "gemini", "model": "gemini-test-model"}]
    assert "SECRET-GEMINI-KEY" not in r.text
