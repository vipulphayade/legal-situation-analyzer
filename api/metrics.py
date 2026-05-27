from __future__ import annotations

from prometheus_client import Counter, Histogram


API_REQUEST_COUNT = Counter(
    "legal_analyzer_api_requests_total",
    "Total API requests handled by the backend.",
    ("method", "path", "status"),
)

API_REQUEST_LATENCY = Histogram(
    "legal_analyzer_api_request_duration_seconds",
    "API request latency in seconds.",
    ("method", "path"),
)

RETRIEVAL_LATENCY = Histogram(
    "legal_analyzer_retrieval_duration_seconds",
    "Retrieval pipeline latency in seconds.",
)

RERANKER_LATENCY = Histogram(
    "legal_analyzer_reranker_duration_seconds",
    "Reranker latency in seconds.",
)

NEGATIVE_SCORE_COUNT = Counter(
    "legal_analyzer_negative_score_total",
    "Count of candidates with non-positive retrieval scores.",
)

APPLICABILITY_FILTER_NEGATIVE_COUNT = Counter(
    "legal_analyzer_applicability_filter_negative_total",
    "Count of candidates rejected by applicability filtering.",
)

RETRIEVAL_FAILURE_COUNT = Counter(
    "legal_analyzer_retrieval_failures_total",
    "Count of retrieval failures or no-match retrieval outcomes.",
)
