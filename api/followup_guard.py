from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FollowupDecision:
    allowed: bool
    reason: str


def validate_followup_relationship(relationship: str, followup_count: int) -> dict[str, object]:
    if followup_count >= 5:
        return {"allowed": False, "reason": "followup_limit_reached"}

    if relationship not in {"follow_up", "related", "clarify"}:
        return {"allowed": False, "reason": "unrelated_query"}

    return {"allowed": True, "reason": "ok"}
