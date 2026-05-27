from __future__ import annotations

from dataclasses import dataclass, field


TOPIC_KEYWORDS = {
    "parking": ["parking", "slot", "stilt", "vehicle", "allotment"],
    "maintenance": ["maintenance", "charges", "billing", "sinking fund", "repairs"],
    "transfer": ["transfer", "share certificate", "nominee", "heir", "successor"],
    "agm": ["agm", "annual general body", "general body", "quorum", "resolution", "notice"],
    "audit": ["audit", "accounts", "books of account", "ledger", "rectification"],
    "redevelopment": ["redevelopment", "conveyance", "deemed conveyance", "developer"],
    "membership": ["membership", "member", "admission", "associate", "nominal"],
    "complaint": ["complaint", "grievance", "registrar", "court", "redressal"],
}

BROAD_QUERY_CLARIFIERS = {
    "agm": [
        "Is this about quorum, notice, voting, minutes, or the validity of a resolution?",
        "Was the issue about an annual general body meeting or a special general meeting?",
    ],
    "parking": [
        "Is this about allocation, visitor parking, unfair preference, or charges?",
    ],
    "maintenance": [
        "Is this about maintenance bills, sinking fund use, repairs, or service charges?",
    ],
    "transfer": [
        "Is this about transfer documents, nomination, share certificate, or approval delay?",
    ],
    "redevelopment": [
        "Is this about member consent, developer selection, tender process, or project transparency?",
    ],
}


@dataclass(frozen=True)
class QueryInsight:
    topic: str
    tokens: list[str] = field(default_factory=list)
    is_broad: bool = False
    clarification_questions: list[str] = field(default_factory=list)


def detect_topic(query: str) -> QueryInsight:
    lowered = query.lower()
    tokens = [token for token in lowered.replace("/", " ").replace("-", " ").split() if token]
    best_topic = "general"
    best_score = 0

    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in lowered)
        if score > best_score:
            best_topic = topic
            best_score = score

    meaningful_tokens = [token for token in tokens if len(token) > 2]
    is_broad = len(meaningful_tokens) <= 3 or best_score == 0
    clarification_questions = BROAD_QUERY_CLARIFIERS.get(best_topic, []) if is_broad else []

    return QueryInsight(
        topic=best_topic,
        tokens=meaningful_tokens,
        is_broad=is_broad,
        clarification_questions=clarification_questions,
    )
