from __future__ import annotations

import logging
import os
import secrets

from fastapi import Header, HTTPException, status


logger = logging.getLogger(__name__)
_audit_logger = logging.getLogger("audit")


def _is_production() -> bool:
    return os.getenv("PRODUCTION", "0").strip().lower() in ("1", "true", "yes")


def _audit_log(event: str, detail: str, request_info: str = "") -> None:
    _audit_logger.info("AUDIT event=%s detail=%s %s", event, detail, request_info)


def verify_api_key(x_api_key: str | None = Header(None)) -> None:
    api_key = os.getenv("API_KEY")
    production = _is_production()

    if not api_key:
        if production:
            _audit_log("auth_fail", "API_KEY unset in production; auth unavailable")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Server misconfigured: authentication not available.",
            )
        logger.warning("No API_KEY configured; authentication is DISABLED")
        return

    if not x_api_key or not secrets.compare_digest(x_api_key, api_key):
        _audit_log("auth_fail", "invalid or missing API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )

    _audit_log("auth_ok", "API key verified")
