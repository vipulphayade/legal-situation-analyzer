import asyncio
import logging
import os
import sys
import threading
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from database import SessionLocal, engine, get_db, run_migrations
from import_service import ensure_seed_data
from metrics import API_REQUEST_COUNT, API_REQUEST_LATENCY, DB_POOL_GAUGE
from auth import verify_api_key
from session_store import session_store
from schemas import AnalyzeRequest, AnalyzeResponse, FollowupRequest, FollowupResponse
from search import analyze_description, answer_followup


_LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(stream=sys.stdout, format=_LOG_FORMAT, level=_LOG_LEVEL)
logger = logging.getLogger(__name__)
_audit_logger = logging.getLogger("audit")
logger.info("Starting Legal Situation Analyzer API v4.0.0")
logger.info("Log level: %s", _LOG_LEVEL)

_active_requests = 0
_active_requests_lock = asyncio.Lock()
_POOL_METRICS_INTERVAL = int(os.getenv("POOL_METRICS_INTERVAL", "15"))


def _audit(event: str, detail: str = "", extra: str = "") -> None:
    _audit_logger.info("AUDIT event=%s detail=%s %s", event, detail, extra)


_MAX_REQUEST_BODY_SIZE = int(os.getenv("MAX_REQUEST_BODY_SIZE", "65536"))


class RequestBodySizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length_str = request.headers.get("content-length")
        if content_length_str:
            try:
                content_length = int(content_length_str)
                if content_length > _MAX_REQUEST_BODY_SIZE:
                    _audit(
                        "request_body_too_large",
                        f"Content-Length: {content_length}",
                        f"path={request.url.path}",
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "success": False,
                            "message": f"Request body exceeds maximum size of {_MAX_REQUEST_BODY_SIZE} bytes.",
                        },
                    )
            except (ValueError, TypeError):
                pass
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


_REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))


class TimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await asyncio.wait_for(call_next(request), timeout=_REQUEST_TIMEOUT)
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"success": False, "message": "Request timed out."},
            )


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        global _active_requests
        async with _active_requests_lock:
            _active_requests += 1
        start = time.perf_counter()
        status = "500"
        try:
            response = await call_next(request)
            status = str(response.status_code)
            return response
        finally:
            async with _active_requests_lock:
                _active_requests -= 1
            route = getattr(request.scope.get("route"), "path", request.url.path)
            API_REQUEST_LATENCY.labels(request.method, route).observe(time.perf_counter() - start)
            API_REQUEST_COUNT.labels(request.method, route, status).inc()


def _report_pool_metrics() -> None:
    """Periodically report DB pool status via Prometheus Gauge."""
    def _loop() -> None:
        while True:
            try:
                pool = engine.pool
                DB_POOL_GAUGE.labels(state="size").set(pool.size())
                DB_POOL_GAUGE.labels(state="checkedin").set(pool.checkedin())
                DB_POOL_GAUGE.labels(state="overflow").set(pool.overflow())
            except Exception:
                logger.warning("Pool metrics collection failed", exc_info=True)
            time.sleep(_POOL_METRICS_INTERVAL)

    thread = threading.Thread(target=_loop, daemon=True, name="pool-metrics")
    thread.start()


def _validate_env() -> None:
    """Validate production-critical environment variables.

    In production mode (PRODUCTION=1), fails startup on placeholders or missing values.
    In development mode, logs warnings but allows startup.
    """
    production = os.getenv("PRODUCTION", "0").strip().lower() in ("1", "true", "yes")
    prefix = logger.critical if production else logger.warning
    action = "Refusing to start." if production else "Set production credentials before deploying externally."

    api_key = os.getenv("API_KEY", "")
    if not api_key:
        prefix("API_KEY is not set. Authentication is disabled. %s", action)
        if production:
            raise RuntimeError("API_KEY is required in production mode. Set a strong random API_KEY and restart.")
    elif api_key in ("change-this-before-production", "your-api-key-here"):
        prefix("API_KEY is set to a placeholder value (%r). %s", api_key, action)
        if production:
            raise RuntimeError(f"API_KEY is a placeholder ({api_key!r}). Generate a strong random key and update .env.")

    db_password = os.getenv("DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD", "")
    if not db_password:
        prefix("DB_PASSWORD / POSTGRES_PASSWORD is not set. %s", action)
        if production:
            raise RuntimeError("DB_PASSWORD is required in production mode. Set a strong random password and restart.")
    elif db_password in ("change-this-before-production", "postgres", "password", "changeme"):
        prefix("DB_PASSWORD / POSTGRES_PASSWORD is set to a placeholder value (%r). %s", db_password, action)
        if production:
            raise RuntimeError(f"DB_PASSWORD is a placeholder ({db_password!r}). Generate a strong random password and update .env.")


def parse_csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _proxy_key_func(request: Request) -> str:
    """Use X-Forwarded-For when behind a reverse proxy, fall back to remote addr."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip.strip()
    return get_remote_address(request)


app = FastAPI(
    title="Legal Situation Analyzer API",
    version="4.0.0",
    description=(
        "Analyzes a housing society situation and maps it to the most relevant "
        "Maharashtra Cooperative Housing Society Model Bye-law."
    ),
)
limiter = Limiter(key_func=_proxy_key_func)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception on %s %s", request.method, request.url.path, exc_info=True)
    _audit("unhandled_exception", f"path={request.url.path} method={request.method}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Internal server error. Please try again later."},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning("Validation error on %s %s: %s", request.method, request.url.path, str(exc)[:200])
    _audit("validation_failure", f"path={request.url.path}")
    return JSONResponse(
        status_code=422,
        content={"success": False, "message": "Invalid request body."},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail},
    )

app.add_middleware(RequestBodySizeMiddleware)
app.add_middleware(TimeoutMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_csv_env(
        "API_ALLOWED_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080"
    ),
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "X-API-Key"],
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=parse_csv_env("ALLOWED_HOSTS", "localhost,127.0.0.1,api,frontend"),
)


@app.on_event("startup")
def on_startup() -> None:
    """Initialize the application: run migrations, validate data, clean sessions."""
    allowed_origins = os.getenv("API_ALLOWED_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080")
    if "localhost" in allowed_origins or "127.0.0.1" in allowed_origins:
        logger.warning(
            "CORS: Using default origins (contains localhost). "
            "Set API_ALLOWED_ORIGINS env-var to your production domain before deploying externally."
        )
    rate_limit = os.getenv("API_RATE_LIMIT", "20/minute")
    logger.info("Allowed origins: %s", allowed_origins)
    logger.info("Rate limit: %s", rate_limit)
    logger.info("DB_PASSWORD set: %s", "yes" if os.getenv("DB_PASSWORD") else "no")

    _validate_env()

    try:
        run_migrations()
        logger.info("Migrations complete")
    except Exception as exc:
        logger.critical("Migration failed: %s", exc, exc_info=True)
        raise

    session = SessionLocal()
    try:
        ensure_seed_data(session)
        session_store.delete_expired(session)
        logger.info("Seed data verified, expired sessions cleaned")
    except Exception as exc:
        logger.critical("Seed data check failed: %s", exc, exc_info=True)
        raise
    finally:
        session.close()

    logger.info("Startup complete — ready to serve traffic")

    _report_pool_metrics()


@app.on_event("shutdown")
def on_shutdown() -> None:
    logger.info("Shutting down — draining in-flight requests")
    import time as _time
    _drain_start = _time.monotonic()
    _drain_timeout = 25
    while _active_requests > 0 and (_time.monotonic() - _drain_start) < _drain_timeout:
        logger.info("Waiting for %d active request(s) to complete...", _active_requests)
        _time.sleep(1)
    if _active_requests > 0:
        logger.warning("Drain timeout reached with %d active request(s) still in flight", _active_requests)
    else:
        logger.info("All in-flight requests completed")
    SessionLocal().close_all()
    logger.info("Database connections closed")


@app.get("/health")
def health_check() -> dict[str, str]:
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "ok", "database": "connected"}
    except SQLAlchemyError as exc:
        logger.error("Health check failed: DB unreachable: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "disconnected"},
        )


@app.get("/metrics")
@limiter.exempt
def metrics(request: Request, _auth: None = Depends(verify_api_key)) -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/analyze", response_model=AnalyzeResponse)
@limiter.limit(os.getenv("API_RATE_LIMIT", "20/minute"))
def analyze(
    request: Request,
    payload: AnalyzeRequest,
    db: Session = Depends(get_db),
    _auth: None = Depends(verify_api_key),
) -> AnalyzeResponse:
    del request
    try:
        result = analyze_description(payload.description, db)
    except SQLAlchemyError as exc:
        logger.error("DB error in analyze: %s", exc, exc_info=True)
        result = {
            "law": "Maharashtra Cooperative Housing Society Model Bye-laws",
            "section": None, "subsection": None, "title": None,
            "statement": "Temporarily unavailable due to a database issue.",
            "explanation": "", "why_this_applies": "",
            "practical_guidance": "Please try again in a few moments.",
            "citation": "", "example": "",
            "conditions_required": [], "possible_challenges": [],
            "related_statutes": [], "related_rules": [], "related_bylaws": [],
            "confidence": 0.0, "success": True,
            "match_type": "service_unavailable",
            "needs_clarification": True,
            "clarification_questions": [],
            "when_may_not_apply": [],
            "recommended_next_steps": [],
            "documents_to_collect": [],
            "possible_authorities": [],
            "confidence_label": "Service Unavailable",
        }
    except Exception as exc:
        logger.error("Unexpected error in analyze: %s", exc, exc_info=True)
        result = {
            "law": "Maharashtra Cooperative Housing Society Model Bye-laws",
            "section": None, "subsection": None, "title": None,
            "statement": "An unexpected error occurred while processing your query.",
            "explanation": "", "why_this_applies": "",
            "practical_guidance": "Please try again.",
            "citation": "", "example": "",
            "conditions_required": [], "possible_challenges": [],
            "related_statutes": [], "related_rules": [], "related_bylaws": [],
            "confidence": 0.0, "success": False,
            "match_type": "error",
            "needs_clarification": True,
            "clarification_questions": [],
            "when_may_not_apply": [],
            "recommended_next_steps": [],
            "documents_to_collect": [],
            "possible_authorities": [],
            "confidence_label": "Service Unavailable",
        }
    session_context = {
        k: result.get(k)
        for k in ("section", "subsection", "title", "citation", "statement",
                  "confidence", "possible_challenges", "documents_to_collect",
                  "topic", "why_this_applies", "recommended_next_steps",
                  "plain_english_summary", "common_disputes")
        if result.get(k) is not None
    }
    related = result.get("related_bylaws") or []
    if related:
        session_context["related_bylaws"] = [
            {"section": r.get("section"), "title": r.get("title")}
            for r in related[:3]
        ]
    result["session_token"] = session_store.create(db, session_context)
    return AnalyzeResponse(**result)


@app.post("/followup", response_model=FollowupResponse)
@limiter.limit(os.getenv("API_RATE_LIMIT", "20/minute"))
def followup(
    request: Request,
    payload: FollowupRequest,
    db: Session = Depends(get_db),
    _auth: None = Depends(verify_api_key),
) -> FollowupResponse:
    del request
    try:
        if payload.session_token:
            stored = session_store.get(db, payload.session_token)
            if stored is not None:
                result = answer_followup(payload.question, stored)
                return FollowupResponse(**result)
        if payload.context:
            logger.warning(
                "DEPRECATED: follow-up with client-provided context (no session_token). "
                "Update the frontend to send session_token instead."
            )
            result = answer_followup(payload.question, payload.context)
            return FollowupResponse(**result)
    except Exception as exc:
        logger.error("Follow-up error: %s", exc, exc_info=True)
        return FollowupResponse(
            section=None, subsection=None, title=None,
            answer="An error occurred while processing your follow-up. Please try again.",
            citation="", confidence=0.0,
        )
    return FollowupResponse(
        section=None, subsection=None, title=None,
        answer="Session expired. Please re-run the analysis.",
        citation="", confidence=0.0,
    )
