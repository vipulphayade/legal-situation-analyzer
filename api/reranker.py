"""Cross-encoder reranker using sentence-transformers.

Reranks top-k candidates by computing query-candidate cross-encoder scores.
Designed as a drop-in module for the benchmark evaluation.
"""

from __future__ import annotations

import time
from functools import lru_cache

from sentence_transformers import CrossEncoder


_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoder:
    return CrossEncoder(_RERANKER_MODEL)


def rerank(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    """Score top-k candidates with a cross-encoder and return them re-sorted."""
    if not candidates:
        return candidates

    model = get_reranker()
    texts = [candidate_text(c) for c in candidates]
    pairs = [(query, t) for t in texts]

    scores = model.predict(pairs, show_progress_bar=False)
    for c, s in zip(candidates, scores):
        c["rerank_score"] = float(s)

    candidates.sort(key=lambda c: c["rerank_score"], reverse=True)
    return candidates[:top_k]


def candidate_text(candidate: dict) -> str:
    parts = [
        str(candidate.get("primary_retrieval_text") or ""),
        str(candidate.get("source_grounded_official_text") or ""),
        str(candidate.get("official_excerpt") or ""),
    ]
    return " ".join(p for p in parts if p)
