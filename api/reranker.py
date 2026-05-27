# Starter reranker scaffold
# Replace with actual model loading in production.

import time

from metrics import RERANKER_LATENCY


class Reranker:
    def rerank(self, query, candidates):
        start = time.perf_counter()
        try:
            return sorted(
                candidates,
                key=lambda x: x.get("final_score", 0),
                reverse=True
            )
        finally:
            RERANKER_LATENCY.observe(time.perf_counter() - start)
