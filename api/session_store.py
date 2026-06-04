from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class SessionStore:
    """PostgreSQL-backed session store with TTL expiry.

    Sessions are shared across all replicas via the database.
    Expired entries are cleaned up lazily on get() and explicitly on startup.
    The session_store table is created by Alembic migration 002.
    """

    def create(self, db: Session, context: dict[str, Any]) -> str:
        token = uuid.uuid4().hex
        db.execute(
            text("INSERT INTO session_store (token, data) VALUES (:token, :data)"),
            {"token": token, "data": json.dumps(context)},
        )
        db.commit()
        return token

    def get(self, db: Session, token: str) -> dict[str, Any] | None:
        row = db.execute(
            text(
                "SELECT data, created_at FROM session_store "
                "WHERE token = :token AND created_at > NOW() - INTERVAL '300 seconds'"
            ),
            {"token": token},
        ).mappings().one_or_none()
        if row is None:
            return None
        data = row["data"]
        return json.loads(data) if isinstance(data, str) else data

    def delete_expired(self, db: Session) -> None:
        """Remove all expired sessions.  Called at startup."""
        db.execute(
            text(
                "DELETE FROM session_store "
                "WHERE created_at < NOW() - INTERVAL '300 seconds'"
            )
        )
        db.commit()


session_store = SessionStore()
