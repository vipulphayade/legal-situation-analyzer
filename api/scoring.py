def calculate_final_score(
    semantic_similarity: float,
    fts_score: float,
    actor_match: float,
    issue_match: float,
    procedural_match: float,
    scenario_match: float,
    negative_applicability: bool,
):
    score = (
        semantic_similarity * 0.20
        + fts_score * 0.15
        + actor_match * 0.20
        + issue_match * 0.20
        + procedural_match * 0.20
        + scenario_match * 0.05
    )

    if negative_applicability:
        score -= 0.40

    return round(score, 4)
