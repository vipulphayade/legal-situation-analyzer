from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram


_LATENCY_BUCKETS = [0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, 15.0, 30.0]


DB_POOL_GAUGE = Gauge(
    "legal_analyzer_db_pool",
    "Database connection pool status.",
    ("state",),
)

API_REQUEST_COUNT = Counter(
    "legal_analyzer_api_requests_total",
    "Total API requests handled by the backend.",
    ("method", "path", "status"),
)

API_REQUEST_LATENCY = Histogram(
    "legal_analyzer_api_request_duration_seconds",
    "API request latency in seconds.",
    ("method", "path"),
    buckets=_LATENCY_BUCKETS,
)

RETRIEVAL_LATENCY = Histogram(
    "legal_analyzer_retrieval_duration_seconds",
    "Retrieval pipeline latency in seconds.",
    buckets=_LATENCY_BUCKETS,
)

NEGATIVE_SCORE_COUNT = Counter(
    "legal_analyzer_negative_score_total",
    "Count of candidates with non-positive retrieval scores.",
)

RETRIEVAL_FAILURE_COUNT = Counter(
    "legal_analyzer_retrieval_failures_total",
    "Count of retrieval failures or no-match retrieval outcomes.",
)

RERANKER_LATENCY = Histogram(
    "legal_analyzer_reranker_duration_seconds",
    "Cross-encoder reranker latency in seconds.",
    buckets=_LATENCY_BUCKETS,
)

CANDIDATE_COUNT = Histogram(
    "legal_analyzer_candidate_count",
    "Number of candidates fetched for scoring.",
    buckets=[1, 5, 10, 25, 50, 100, 150, 200, 250, 300],
)

TOP_SCORE = Histogram(
    "legal_analyzer_top_score",
    "Heuristic score of the best candidate before reranking.",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

FINAL_CONFIDENCE = Histogram(
    "legal_analyzer_final_confidence",
    "Final confidence score returned in the response.",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

MATCH_TYPE_COUNT = Counter(
    "legal_analyzer_match_type_total",
    "Count of query resolution outcomes by type.",
    ("match_type",),
)

TOPIC_PREFILTER_COUNT = Counter(
    "legal_analyzer_topic_prefilter_total",
    "Count of queries where topic-based prefiltering was active vs inactive.",
    ("active",),
)

CLARIFICATION_COUNT = Counter(
    "legal_analyzer_clarification_total",
    "Count of queries where clarification was flagged vs not.",
    ("needed",),
)
