"""Security-focused tests.

Covers: fail-closed auth, audit logging, secret redaction,
request body size limits, validation hardening, security headers,
and error response sanitization.
"""

from __future__ import annotations

import io
import logging
import os
import re

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from auth import verify_api_key
from main import app, _MAX_REQUEST_BODY_SIZE, RequestBodySizeMiddleware


# ========================================================================
# Auth — production fail-closed behavior
# ========================================================================


class TestAuthProductionFailClosed:
    """In production, missing API_KEY must not silently disable auth."""

    def make_app(self) -> FastAPI:
        app = FastAPI()

        @app.get("/protected")
        def protected(_auth: None = Depends(verify_api_key)) -> dict[str, str]:
            return {"status": "ok"}

        return app

    def test_production_fails_when_no_key(self) -> None:
        os.environ["PRODUCTION"] = "1"
        saved = os.environ.pop("API_KEY", None)
        try:
            app = self.make_app()
            client = TestClient(app, base_url="http://localhost")
            resp = client.get("/protected")
            assert resp.status_code == 503
            data = resp.json()
            assert "authentication not available" in data.get("detail", "").lower()
        finally:
            if saved is not None:
                os.environ["API_KEY"] = saved
            os.environ.pop("PRODUCTION", None)

    def test_production_fails_when_empty_key(self) -> None:
        os.environ["PRODUCTION"] = "1"
        os.environ["API_KEY"] = ""
        try:
            app = self.make_app()
            client = TestClient(app, base_url="http://localhost")
            resp = client.get("/protected")
            assert resp.status_code == 503
        finally:
            os.environ.pop("PRODUCTION", None)
            os.environ.pop("API_KEY", None)

    def test_development_allows_no_key(self) -> None:
        saved = os.environ.pop("API_KEY", None)
        os.environ.pop("PRODUCTION", None)
        try:
            app = self.make_app()
            client = TestClient(app, base_url="http://localhost")
            resp = client.get("/protected")
            assert resp.status_code == 200
        finally:
            if saved is not None:
                os.environ["API_KEY"] = saved


class TestAuthSuccessFailure:
    """Auth accepts correct key, rejects wrong/missing key."""

    @pytest.fixture
    def clear_env(self) -> None:
        saved_key = os.environ.pop("API_KEY", None)
        saved_prod = os.environ.pop("PRODUCTION", None)
        yield
        if saved_key is not None:
            os.environ["API_KEY"] = saved_key
        if saved_prod is not None:
            os.environ["PRODUCTION"] = saved_prod

    def test_auth_accepted_when_correct_key(self, clear_env: None) -> None:
        os.environ["API_KEY"] = "test-key-123"
        app = FastAPI()

        @app.get("/protected")
        def protected(_auth: None = Depends(verify_api_key)) -> dict[str, str]:
            return {"status": "ok"}

        client = TestClient(app, base_url="http://localhost")
        resp = client.get("/protected", headers={"X-API-Key": "test-key-123"})
        assert resp.status_code == 200

    def test_auth_rejected_when_wrong_key(self, clear_env: None) -> None:
        os.environ["API_KEY"] = "test-key-123"
        app = FastAPI()

        @app.get("/protected")
        def protected(_auth: None = Depends(verify_api_key)) -> dict[str, str]:
            return {"status": "ok"}

        client = TestClient(app, base_url="http://localhost")
        resp = client.get("/protected", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 401

    def test_auth_rejected_when_no_header(self, clear_env: None) -> None:
        os.environ["API_KEY"] = "test-key-123"
        app = FastAPI()

        @app.get("/protected")
        def protected(_auth: None = Depends(verify_api_key)) -> dict[str, str]:
            return {"status": "ok"}

        client = TestClient(app, base_url="http://localhost")
        resp = client.get("/protected")
        assert resp.status_code == 401


# ========================================================================
# Request body size limits
# ========================================================================


class TestRequestBodySizeLimit:
    """RequestBodySizeMiddleware rejects oversized payloads with 413."""

    @pytest.fixture
    def size_app(self) -> FastAPI:
        app = FastAPI()
        app.add_middleware(RequestBodySizeMiddleware)

        @app.post("/test")
        async def test_endpoint() -> dict[str, str]:
            return {"status": "ok"}

        return app

    def test_accepts_reasonable_body(self, size_app: FastAPI) -> None:
        client = TestClient(size_app, base_url="http://localhost")
        body = "x" * 1000
        resp = client.post("/test", content=body, headers={"Content-Type": "text/plain"})
        assert resp.status_code == 200

    def test_rejects_oversized_body(self, size_app: FastAPI) -> None:
        client = TestClient(size_app, base_url="http://localhost")
        body = "x" * (_MAX_REQUEST_BODY_SIZE + 1)
        resp = client.post("/test", content=body, headers={"Content-Type": "text/plain"})
        assert resp.status_code == 413
        data = resp.json()
        assert "exceeds maximum size" in data.get("message", "").lower()

    def test_accepts_body_at_limit(self, size_app: FastAPI) -> None:
        client = TestClient(size_app, base_url="http://localhost")
        body = "x" * _MAX_REQUEST_BODY_SIZE
        resp = client.post("/test", content=body, headers={"Content-Type": "text/plain"})
        assert resp.status_code == 200


# ========================================================================
# Validation hardening — FollowupRequest schema
# ========================================================================


class TestFollowupRequestValidation:
    """session_token and question validation."""

    def test_rejects_long_session_token(self) -> None:
        from schemas import FollowupRequest

        with pytest.raises(Exception):
            FollowupRequest(
                question="test question",
                session_token="a" * 200,
            )

    def test_rejects_non_alphanumeric_session_token(self) -> None:
        from schemas import FollowupRequest

        with pytest.raises(Exception):
            FollowupRequest(
                question="test question",
                session_token="abc-123!",
            )

    def test_accepts_valid_session_token(self) -> None:
        from schemas import FollowupRequest

        req = FollowupRequest(
            question="test question",
            session_token="abc123def456",
        )
        assert req.session_token == "abc123def456"

    def test_accepts_empty_session_token(self) -> None:
        from schemas import FollowupRequest

        req = FollowupRequest(question="test question")
        assert req.session_token == ""


# ========================================================================
# Error response sanitization — no Pydantic details leaked to client
# ========================================================================


class TestErrorResponseSanitization:
    """API error responses must not expose internal details."""

    def test_validation_error_no_details_in_response(self) -> None:
        client = TestClient(app, base_url="http://localhost")

        from auth import verify_api_key as vak
        app.dependency_overrides[vak] = lambda: None

        try:
            resp = client.post(
                "/analyze",
                json={"description": "short"},
            )
            assert resp.status_code == 422
            data = resp.json()
            assert "message" in data
            assert "details" not in data, (
                "Validation error response must not contain 'details' field"
            )
        finally:
            app.dependency_overrides.clear()

    def test_global_error_does_not_include_traceback(self) -> None:
        client = TestClient(app, base_url="http://localhost")

        from auth import verify_api_key as vak
        app.dependency_overrides[vak] = lambda: None

        try:
            resp = client.get("/nonexistent-endpoint-xyz")
            assert resp.status_code in (404, 405)
            data = resp.json()
            assert "traceback" not in str(data).lower()
        finally:
            app.dependency_overrides.clear()


# ========================================================================
# Security headers
# ========================================================================


class TestSecurityHeaders:
    """All expected security headers are present on responses."""

    def test_security_headers_present(self) -> None:
        client = TestClient(app, base_url="http://localhost")

        resp = client.get("/health")
        headers = resp.headers

        assert headers.get("x-content-type-options") == "nosniff"
        assert headers.get("x-frame-options") == "DENY"
        assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        assert headers.get("cache-control") == "no-store"
        assert "geolocation=()" in headers.get("permissions-policy", "")


# ========================================================================
# Secret redaction in logs
# ========================================================================


class TestSecretRedaction:
    """Sensitive values must not appear in log output."""

    def test_validation_error_logged_without_body(self) -> None:
        """Validation error logs must not contain sensitive input data."""
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        test_logger = logging.getLogger("test_security")
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.WARNING)

        from pydantic import BaseModel, Field
        from fastapi.exceptions import RequestValidationError
        from starlette.responses import JSONResponse

        local_app = FastAPI()

        @local_app.exception_handler(RequestValidationError)
        async def local_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
            test_logger.warning(
                "Validation error on %s %s: %s",
                request.method, request.url.path, str(exc)[:200]
            )
            return JSONResponse(
                status_code=422,
                content={"success": False, "message": "Invalid request body."},
            )

        class TestModel(BaseModel):
            name: str = Field(..., min_length=5)

        @local_app.post("/test")
        async def ep(payload: TestModel) -> dict:
            return {"ok": True}

        client = TestClient(local_app, base_url="http://localhost")
        long_input = "ab"
        try:
            resp = client.post("/test", json={"name": long_input})
            assert resp.status_code == 422
        finally:
            test_logger.removeHandler(handler)

        log_output = stream.getvalue()
        assert long_input not in log_output, (
            "Short input leaked — validation error log must not echo input data"
        )


# ========================================================================
# Audit logging
# ========================================================================


class TestAuditLogging:
    """Audit events are emitted for auth, validation, and request events."""

    def test_auth_failure_triggers_audit_log(self) -> None:
        stream = io.StringIO()
        audit_logger = logging.getLogger("audit")
        handler = logging.StreamHandler(stream)
        audit_logger.addHandler(handler)
        audit_logger.setLevel(logging.INFO)

        os.environ["API_KEY"] = "secret-key-456"
        try:
            app_local = FastAPI()

            @app_local.get("/protected")
            def protected(_auth: None = Depends(verify_api_key)) -> dict[str, str]:
                return {"status": "ok"}

            client = TestClient(app_local, base_url="http://localhost")
            resp = client.get("/protected", headers={"X-API-Key": "wrong-key"})
        finally:
            audit_logger.removeHandler(handler)
            os.environ.pop("API_KEY", None)

        log_output = stream.getvalue()
        assert "AUDIT" in log_output
        assert "auth_fail" in log_output

    def test_auth_success_triggers_audit_log(self) -> None:
        stream = io.StringIO()
        audit_logger = logging.getLogger("audit")
        handler = logging.StreamHandler(stream)
        audit_logger.addHandler(handler)
        audit_logger.setLevel(logging.INFO)

        os.environ["API_KEY"] = "secret-key-456"
        try:
            app_local = FastAPI()

            @app_local.get("/protected")
            def protected(_auth: None = Depends(verify_api_key)) -> dict[str, str]:
                return {"status": "ok"}

            client = TestClient(app_local, base_url="http://localhost")
            resp = client.get("/protected", headers={"X-API-Key": "secret-key-456"})
        finally:
            audit_logger.removeHandler(handler)
            os.environ.pop("API_KEY", None)

        log_output = stream.getvalue()
        assert "AUDIT" in log_output
        assert "auth_ok" in log_output

    def test_oversized_request_triggers_audit_log(self) -> None:
        stream = io.StringIO()
        audit_logger = logging.getLogger("audit")
        handler = logging.StreamHandler(stream)
        audit_logger.addHandler(handler)
        audit_logger.setLevel(logging.INFO)

        app_local = FastAPI()
        app_local.add_middleware(RequestBodySizeMiddleware)

        @app_local.post("/test")
        async def test_endpoint() -> dict[str, str]:
            return {"status": "ok"}

        client = TestClient(app_local, base_url="http://localhost")
        body = "x" * (_MAX_REQUEST_BODY_SIZE + 1)
        resp = client.post("/test", content=body, headers={"Content-Type": "text/plain"})

        audit_logger.removeHandler(handler)
        log_output = stream.getvalue()
        assert "AUDIT" in log_output
        assert "request_body_too_large" in log_output


# ========================================================================
# .env not in docker build context
# ========================================================================


def test_dockerignore_excludes_env() -> None:
    """Verify .dockerignore contains .env."""
    import pathlib

    dockerignore_path = pathlib.Path(__file__).resolve().parent.parent / ".dockerignore"
    content = dockerignore_path.read_text()
    assert ".env" in content, ".dockerignore must exclude .env"
    assert ".env.local" in content, ".dockerignore must exclude .env.local"
