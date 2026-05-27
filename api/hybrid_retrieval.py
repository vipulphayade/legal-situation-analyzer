from scoring import calculate_final_score
from drift_prevention import apply_drift_prevention
from metrics import NEGATIVE_SCORE_COUNT

def hybrid_search(query, candidates, query_topic):
    filtered = []

    for c in candidates:
        score = calculate_final_score(
            semantic_similarity=c.get("semantic_similarity", 0.0),
            fts_score=c.get("fts_score", 0.0),
            actor_match=c.get("actor_match", 0.0),
            issue_match=c.get("issue_match", 0.0),
            procedural_match=c.get("procedural_match", 0.0),
            scenario_match=c.get("scenario_match", 0.0),
            negative_applicability=False,
        )

        score = apply_drift_prevention(
            query_topic,
            c.get("topic_group", ""),
            score,
        )

        if score <= 0:
            NEGATIVE_SCORE_COUNT.inc()

        c["final_score"] = score
        filtered.append(c)

    return sorted(filtered, key=lambda x: x["final_score"], reverse=True)[:5]
