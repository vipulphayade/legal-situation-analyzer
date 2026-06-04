from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


client = TestClient(app, base_url="http://localhost")


def test_health_returns_ok() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "database" in data


def test_metrics_returns_prometheus() -> None:
    resp = client.get("/metrics")
    assert resp.status_code == 200
    content = resp.text
    assert "legal_analyzer_api_requests_total" in content
    assert "legal_analyzer_retrieval_duration_seconds" in content
    assert "legal_analyzer_negative_score_total" in content
    assert "legal_analyzer_retrieval_failures_total" in content
    assert "python_info" in content


def test_metrics_content_type() -> None:
    resp = client.get("/metrics")
    ct = resp.headers.get("content-type", "")
    assert ct.startswith("text/plain; version=")
