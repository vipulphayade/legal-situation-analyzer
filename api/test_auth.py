from __future__ import annotations

import os

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from auth import verify_api_key


@pytest.fixture(autouse=True)
def clear_api_key():
    saved = os.environ.pop("API_KEY", None)
    yield
    if saved is not None:
        os.environ["API_KEY"] = saved
    else:
        os.environ.pop("API_KEY", None)


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()

    @app.get("/protected")
    def protected(_auth: None = Depends(verify_api_key)) -> dict[str, str]:
        return {"status": "ok"}

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app, base_url="http://localhost")


def test_auth_skipped_when_no_key(client: TestClient) -> None:
    """When API_KEY is not set, requests succeed without auth header."""
    resp = client.get("/protected")
    assert resp.status_code == 200


def test_auth_rejected_when_no_header(client: TestClient) -> None:
    """When API_KEY is set, a request without X-API-Key returns 401."""
    os.environ["API_KEY"] = "super-secret"
    resp = client.get("/protected")
    assert resp.status_code == 401
    detail = resp.json().get("detail", "")
    assert "API key" in detail


def test_auth_rejected_when_wrong_key(client: TestClient) -> None:
    """When API_KEY is set, a request with wrong key returns 401."""
    os.environ["API_KEY"] = "super-secret"
    resp = client.get("/protected", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401


def test_auth_accepted_when_correct_key(client: TestClient) -> None:
    """When API_KEY is set, a request with matching key succeeds."""
    os.environ["API_KEY"] = "super-secret"
    resp = client.get("/protected", headers={"X-API-Key": "super-secret"})
    assert resp.status_code == 200
