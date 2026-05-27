def build_explanation(result):
    return {
        "confidence_label": result.get("confidence_label", "Likely Relevant"),
        "why_matched": result.get("why_this_applies", ""),
        "topic_group": result.get("topic_group", ""),
        "issue_category": result.get("issue_category", "")
    }
