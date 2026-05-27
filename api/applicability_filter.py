from metrics import APPLICABILITY_FILTER_NEGATIVE_COUNT


def applicable_to_query(query_topic, candidate):
    candidate_topic = candidate.get("topic_group") or candidate.get("topic") or ""
    if not query_topic or query_topic == "general":
        return True
    applies = query_topic == candidate_topic or query_topic in candidate_topic or candidate_topic in query_topic
    if not applies:
        APPLICABILITY_FILTER_NEGATIVE_COUNT.inc()
    return applies
