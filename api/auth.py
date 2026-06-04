from __future__ import annotations

import logging
import os
import secrets

from fastapi import Header, HTTPException, status


logger = logging.getLogger(__name__)


def verify_api_key(x_api_key: str | None = Header(None)) -> None:
    api_key = os.getenv("API_KEY")
    if not api_key:
        logger.warning("No API_KEY configured; authentication is DISABLED")
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
