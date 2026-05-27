def apply_drift_prevention(query_topic: str, result_topic: str, score: float) -> float:
    if query_topic == result_topic:
        score += 0.25
    else:
        score -= 0.30
    return score
