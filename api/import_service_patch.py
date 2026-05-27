# PATCHED load_dataset validator-compatible logic

def normalize_entry(entry):
    content = (
        entry.get("content")
        or entry.get("plain_english")
        or entry.get("legal_summary")
        or entry.get("official_excerpt")
        or ""
    )

    return {
        "law_name": entry.get(
            "law_name",
            "Maharashtra Cooperative Housing Society Model Bye-laws",
        ),
        "section": str(entry.get("section") or entry.get("bylaw_number") or ""),
        "subsection": entry.get("subsection", "") or "",
        "title": entry.get("title") or f"Bye-law {entry.get('section')}",
        "topic": entry.get("topic")
        or entry.get("topic_group")
        or "model bye-laws",
        "keywords": entry.get("keywords", []),
        "content": content,
        "explanation": entry.get("plain_english")
        or entry.get("explanation")
        or "",
        "example": entry.get("example", ""),
        "conditions_required": entry.get("conditions_required", []),
        "possible_challenges": entry.get("possible_challenges", []),
        "related_statutes": entry.get("related_statutes", []),
    }
