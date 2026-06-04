from __future__ import annotations

from enum import Enum
from query_understanding import QueryInsight


class RetrievalStrategy(str, Enum):
    EXACT_CITATION = "exact_citation"
    KEYWORD_SEMANTIC = "keyword_semantic"
    HYBRID_RERANKER = "hybrid_reranker"


def select_strategy(insight: QueryInsight) -> RetrievalStrategy:
    if insight.section_ref:
        return RetrievalStrategy.EXACT_CITATION

    has_entity = bool(insight.subject) or bool(insight.actor) or bool(insight.action)

    if has_entity and insight.intent:
        return RetrievalStrategy.KEYWORD_SEMANTIC

    has_intent = bool(insight.intent)
    has_focused_topic = insight.topic != "general" and insight.topic_score >= 2

    if has_intent and has_focused_topic:
        return RetrievalStrategy.KEYWORD_SEMANTIC

    return RetrievalStrategy.HYBRID_RERANKER
