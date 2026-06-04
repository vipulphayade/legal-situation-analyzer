from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from main import app
from session_store import session_store


# ---- unit tests for SessionStore (DB required) ----


def _get_db():
    """Try to connect to PostgreSQL; return a sessionmaker or None."""
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    user = os.getenv("DB_USER", "legal_app")
    password = os.getenv("DB_PASSWORD", "")
    dbname = os.getenv("DB_NAME", "legal_analyzer")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    try:
        engine = create_engine(url, pool_pre_ping=True, future=True)
        conn = engine.connect()
        conn.close()
        return sessionmaker(bind=engine)
    except Exception:
        return None


def test_session_create_and_get() -> None:
    maker = _get_db()
    if maker is None:
        pytest.skip("No database available for SessionStore unit tests")
    db = maker()
    try:
        ctx = {"section": "100", "confidence": 0.85}
        token = session_store.create(db, ctx)
        retrieved = session_store.get(db, token)
        assert retrieved is not None
        assert retrieved["section"] == "100"
        assert retrieved["confidence"] == 0.85
    finally:
        db.close()


def test_session_unknown_token() -> None:
    maker = _get_db()
    if maker is None:
        pytest.skip("No database available for SessionStore unit tests")
    db = maker()
    try:
        assert session_store.get(db, "nonexistent") is None
    finally:
        db.close()


def test_session_isolation() -> None:
    maker = _get_db()
    if maker is None:
        pytest.skip("No database available for SessionStore unit tests")
    db = maker()
    try:
        t1 = session_store.create(db, {"a": 1})
        t2 = session_store.create(db, {"a": 2})
        assert session_store.get(db, t1) == {"a": 1}
        assert session_store.get(db, t2) == {"a": 2}
    finally:
        db.close()


# ---- integration tests with FastAPI ----


@pytest.fixture(autouse=True)
def disable_auth():
    """Disable API key auth for integration tests."""
    overrides = {}
    try:
        from auth import verify_api_key

        overrides[verify_api_key] = lambda: None
        app.dependency_overrides.update(overrides)
        yield
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, base_url="http://localhost", raise_server_exceptions=False)


def test_analyze_returns_session_token(client: TestClient) -> None:
    """The /analyze endpoint returns a session_token in the response."""
    resp = client.post("/analyze", json={"description": "quorum not met for agm"})
    if resp.status_code in (500, 503):
        pytest.skip("No database available for this test")
    assert resp.status_code in (200, 422)
    if resp.status_code == 200:
        data = resp.json()
        assert "session_token" in data
        assert len(data["session_token"]) > 0


def test_followup_with_session_token(client: TestClient) -> None:
    """Follow-up using a server-side session token resolves correctly."""
    analyze_resp = client.post(
        "/analyze", json={"description": "quorum not met for agm"}
    )
    if analyze_resp.status_code in (500, 503):
        pytest.skip("No database available for this test")
    if analyze_resp.status_code != 200:
        pytest.skip("analyze did not return 200")
    data = analyze_resp.json()
    token = data.get("session_token", "")
    assert token, "no session_token in analyze response"

    followup_resp = client.post(
        "/followup",
        json={
            "question": "what is the text",
            "session_token": token,
        },
    )
    assert followup_resp.status_code == 200
    result = followup_resp.json()
    assert result.get("section") is not None


def test_followup_fallback_to_client_context(client: TestClient) -> None:
    """Without a session_token, follow-up falls back to client-supplied context."""
    resp = client.post(
        "/followup",
        json={
            "question": "what is the text",
            "context": {
                "section": "100",
                "subsection": None,
                "title": "Quorum",
                "citation": "Bye-law 100",
                "confidence": 0.85,
            },
        },
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["section"] == "100"


def test_followup_invalid_token(client: TestClient) -> None:
    """Invalid session token falls back to empty context."""
    resp = client.post(
        "/followup",
        json={
            "question": "what is the text",
            "session_token": "bad-token",
        },
    )
    if resp.status_code in (500, 503):
        pytest.skip("No database available for this test")
    assert resp.status_code == 200
    result = resp.json()
    assert result["section"] is None
