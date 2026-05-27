from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from bylaw_seed import LAW_NAME
from embeddings import get_embedding_service
from metrics import NEGATIVE_SCORE_COUNT, RETRIEVAL_FAILURE_COUNT, RETRIEVAL_LATENCY
from schemas import DISCLAIMER_TEXT
from query_understanding import detect_topic


STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "had", "has", "have", "he", "her", "his", "if", "in", "into", "is",
    "it", "its", "may", "my", "of", "on", "or", "our", "she", "that",
    "the", "their", "them", "they", "this", "to", "was", "we", "were",
    "what", "when", "which", "who", "will", "with", "without", "you", "your",
    "required", "requirement", "issue", "meeting", "general", "body"
}

SYNONYM_GROUPS = {
    "agm": {"agm", "annual", "general", "body", "meeting"},
    "quorum": {"quorum", "present", "members", "attendance"},
    "notice": {"notice", "intimation", "call", "calling"},
    "voting": {"vote", "voting", "poll", "ballot"},
    "resolution": {"resolution", "decision", "passed", "approve", "approved"},
    "parking": {"parking", "slot", "stilt", "vehicle", "vehicle", "allotment"},
    "maintenance": {"maintenance", "charges", "bill", "billing", "sinking", "fund", "repair"},
    "transfer": {"transfer", "share", "certificate", "nominee", "nomination", "heir", "successor"},
    "redevelopment": {"redevelopment", "developer", "conveyance", "project"},
    "audit": {"audit", "accounts", "books", "records", "ledger"},
    "complaint": {"complaint", "grievance", "registrar", "court", "redressal"},
    "membership": {"member", "membership", "admission", "associate", "nominal"},
    "committee": {"committee", "secretary", "chairman", "management", "managing"},
}

TOPIC_RULES = {
    "agm": {"query_tokens": {"agm", "general", "body", "meeting", "quorum", "notice", "voting", "resolution", "minutes", "special", "adjourned"}},
    "parking": {"query_tokens": {"parking", "stilt", "slot", "vehicle", "allocation", "visitor", "charges"}},
    "maintenance": {"query_tokens": {"maintenance", "charges", "bill", "billing", "sinking", "fund", "repair", "repairs"}},
    "transfer": {"query_tokens": {"transfer", "share", "certificate", "nominee", "nomination", "heir", "inheritance", "succession"}},
    "redevelopment": {"query_tokens": {"redevelopment", "developer", "conveyance", "deemed", "project"}},
    "audit": {"query_tokens": {"audit", "accounts", "books", "records", "ledger", "rectification"}},
    "membership": {"query_tokens": {"member", "membership", "admission", "associate", "nominal", "eligible"}},
    "complaint": {"query_tokens": {"complaint", "grievance", "registrar", "court", "redressal"}},
}



TERM_WEIGHTS = {
    "quorum": 6.0,
    "notice": 2.0,
    "voting": 2.0,
    "resolution": 2.0,
    "meeting": 1.2,
    "annual": 1.6,
    "general": 0.8,
    "body": 0.8,
    "parking": 2.5,
    "maintenance": 2.5,
    "transfer": 2.5,
    "nominee": 2.0,
    "heir": 2.0,
    "audit": 2.5,
    "redevelopment": 2.5,
    "complaint": 2.0,
    "membership": 2.0,
    "committee": 1.5,
    "charges": 1.8,
    "sinking": 1.8,
    "fund": 1.5,
}

# --------------------------------------------------
# BYE-LAW NUMBER DETECTION
# --------------------------------------------------

def detect_bye_law_reference(query: str):
    pattern = r"\b(?:bye[-\s]?law|byelaw|section)\s*(\d{1,3})\s*(?:\(?\s*([a-z])\s*\)?)?\b"
    match = re.search(pattern, query.lower())
    if not match:
        match = re.search(r"\b(\d{1,3})\s*\(\s*([a-z])\s*\)", query.lower())

    if match:
        section = match.group(1)
        subsection = match.group(2).lower() if match.group(2) else ""
        return section, subsection

    return None


def no_match_response(confidence: float = 0.0, clarification_questions: list[str] | None = None):
    return {
        "law": LAW_NAME,
        "section": None,
        "subsection": None,
        "title": "Needs clarification",
        "statement": "",
        "explanation": "Additional facts or documents may be required for reliable interpretation.",
        "why_this_applies": "",
        "practical_guidance": "Please add the exact meeting, parking, maintenance, membership, transfer, or redevelopment issue.",
        "citation": "No reliable exact bye-law match found.",
        "example": "",
        "conditions_required": [],
        "possible_challenges": [],
        "related_statutes": [],
        "related_rules": [],
        "related_bylaws": [],
        "confidence": round(max(0.0, min(1.0, confidence)), 2),
        "confidence_label": "Needs Clarification",
        "disclaimer": DISCLAIMER_TEXT,
        "success": False,
        "message": "No reliable exact bye-law match found.",
        "match_type": "clarification_needed",
        "needs_clarification": True,
        "clarification_questions": clarification_questions or [
            "Which issue is involved: quorum, notice, voting, resolution, parking, maintenance, transfer, or redevelopment?"
        ],
        "possible_topics": ["AGM", "quorum", "voting", "notice", "resolutions"],
        "when_may_not_apply": [],
        "recommended_next_steps": [],
        "documents_to_collect": [],
        "possible_authorities": [],
    }


def ensure_query_log_table(db: Session):
    db.execute(text("""
    CREATE TABLE IF NOT EXISTS query_logs (
        id SERIAL PRIMARY KEY,
        query_text TEXT NOT NULL,
        returned_rule TEXT NOT NULL,
        confidence DOUBLE PRECISION NOT NULL,
        timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """))
    db.commit()


# --------------------------------------------------
# TEXT PROCESSING
# --------------------------------------------------

def tokenize(value: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]+", value.lower())


def extract_keywords(value: str) -> set[str]:
    return {
        token
        for token in tokenize(value)
        if len(token) > 2 and token not in STOP_WORDS
    }


def expand_keywords(keywords: set[str]) -> set[str]:
    expanded = set(keywords)
    for keyword in list(keywords):
        for canonical, variants in SYNONYM_GROUPS.items():
            if keyword == canonical or keyword in variants:
                expanded.add(canonical)
                expanded.update(variants)
    return expanded


def query_topic(query: str) -> str:
    insight = detect_topic(query)
    return insight.topic if insight.topic else "general"


def weighted_overlap(query_terms: set[str], candidate_terms: set[str]) -> float:
    if not query_terms:
        return 0.0

    total = 0.0
    matched = 0.0
    for term in query_terms:
        weight = TERM_WEIGHTS.get(term, 1.0)
        total += weight
        if term in candidate_terms:
            matched += weight
    return min(1.0, matched / max(total, 1e-9))


def candidate_text(candidate: dict[str, Any]) -> str:
    parts = [
        str(candidate.get("retrieval_text") or ""),
        str(candidate.get("official_excerpt") or ""),
        str(candidate.get("normalized_legal_text") or ""),
        str(candidate.get("source_grounded_official_text") or ""),
        str(candidate.get("chapter") or ""),
        str(candidate.get("topic") or ""),
        str(candidate.get("topic_group") or ""),
        str(candidate.get("issue_category") or ""),
        str(candidate.get("section") or ""),
        str(candidate.get("subsection") or ""),
        str(candidate.get("title") or ""),
        " ".join(candidate.get("keywords", []) or []),
        " ".join(candidate.get("technical_terms", []) or []),
    ]
    return " ".join(part for part in parts if part).lower()


def phrase_boost(query_lower: str, candidate_blob: str) -> float:
    boost = 0.0
    pairs = [
        ("general body", "general body"),
        ("annual general body", "annual general body"),
        ("special general meeting", "special general meeting"),
        ("committee meeting", "committee meeting"),
        ("quorum", "quorum"),
        ("parking", "parking"),
        ("sinking fund", "sinking fund"),
        ("redevelopment", "redevelopment"),
        ("transfer", "transfer"),
    ]
    for phrase, needle in pairs:
        if phrase in query_lower and needle in candidate_blob:
            boost += 0.15
    if "quorum" in query_lower and "quorum" in candidate_blob:
        boost += 0.50
    if "quorum" in query_lower and "general body" in candidate_blob:
        boost += 0.12
    if "quorum" in query_lower and "quorum" not in candidate_blob and ("annual general body" in query_lower or "general body" in query_lower):
        boost -= 0.10
    if "start" in query_lower and "quorum" in candidate_blob:
        boost += 0.08
    if "general body" in query_lower and "committee meeting" in candidate_blob and "general body" not in candidate_blob:
        boost -= 0.08
    return max(-0.15, min(0.35, boost))


def parse_embedding(value: Any) -> list[float]:
    if value is None:
        return []
    if isinstance(value, list):
        return [float(item) for item in value]
    if isinstance(value, tuple):
        return [float(item) for item in value]
    if isinstance(value, str):
        raw = value.strip().strip("[]")
        if not raw:
            return []
        return [float(item) for item in raw.split(",") if item.strip()]
    try:
        return [float(item) for item in value]
    except Exception:
        return []


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    size = min(len(a), len(b))
    a = a[:size]
    b = b[:size]
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
    norm_b = math.sqrt(sum(y * y for y in b)) or 1.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


def topic_overlap(query_topic: str, candidate: dict[str, Any]) -> float:
    if not query_topic:
        return 0.0
    candidate_blob = " ".join(
        [
            str(candidate.get("topic") or ""),
            str(candidate.get("topic_group") or ""),
            str(candidate.get("issue_category") or ""),
            str(candidate.get("chapter") or ""),
            str(candidate.get("title") or ""),
            candidate_text(candidate),
        ]
    )
    if query_topic in candidate_blob:
        return 1.0
    if query_topic == "agm" and ("general body" in candidate_blob or "meeting" in candidate_blob or "quorum" in candidate_blob):
        return 0.9
    if query_topic == "parking" and "parking" in candidate_blob:
        return 0.9
    if query_topic == "maintenance" and any(word in candidate_blob for word in ["maintenance", "repairs", "sinking fund", "charges"]):
        return 0.9
    if query_topic == "transfer" and any(word in candidate_blob for word in ["transfer", "nominee", "heir", "share certificate"]):
        return 0.9
    if query_topic == "audit" and any(word in candidate_blob for word in ["audit", "accounts", "books of account", "records"]):
        return 0.9
    if query_topic == "redevelopment" and any(word in candidate_blob for word in ["redevelopment", "conveyance", "developer"]):
        return 0.9
    if query_topic == "membership" and any(word in candidate_blob for word in ["membership", "member", "admission", "associate", "nominal"]):
        return 0.9
    if query_topic == "complaint" and any(word in candidate_blob for word in ["complaint", "registrar", "court", "redressal"]):
        return 0.9
    return 0.0


def query_field_boost(query_terms: set[str], candidate: dict[str, Any]) -> float:
    candidate_terms = extract_keywords(candidate_text(candidate))
    if not query_terms:
        return 0.0
    overlap = len(query_terms & candidate_terms)
    return min(1.0, overlap / max(1, len(query_terms)))




def section_topic_bias(query_lower: str, topic: str, candidate: dict[str, Any]) -> float:
    section = str(candidate.get("section") or "")
    if topic == "agm":
        if any(term in query_lower for term in ["quorum", "notice", "voting", "resolution", "minutes"]):
            if section == "100":
                return 0.28
            if section == "101":
                return 0.18
            if section in {"98", "99"}:
                return 0.12
            if section in {"94", "95", "96", "97", "104", "105", "106", "107", "108", "110"}:
                return 0.06
        if "general body" in query_lower:
            if section in {"94", "95", "100", "101", "98", "99"}:
                return 0.08
    if topic == "parking":
        if section == "78":
            return 0.30
        if section in {"79", "80", "81", "82", "83", "84"}:
            return 0.12
    if topic == "maintenance":
        if section in {"65", "66", "67", "68", "69", "70", "71", "157", "159"}:
            return 0.14
        if section in {"13", "14"}:
            return 0.10
    if topic == "transfer":
        if section in {"32", "33", "34", "35", "36", "37", "38", "39", "40"}:
            return 0.16
    if topic == "redevelopment":
        if section in {"154", "158", "175"}:
            return 0.22
    if topic == "audit":
        if section in {"141", "142", "143", "146", "151", "152", "153"}:
            return 0.20
    if topic == "membership":
        if section in {"16", "17", "18", "19", "20", "21", "22", "23", "24"}:
            return 0.14
    return 0.0


def score_candidate(query_terms: set[str], query_embedding: list[float], candidate: dict[str, Any], topic: str, query_lower: str) -> tuple[float, dict[str, float]]:
    candidate_embedding = parse_embedding(candidate.get("embedding"))
    semantic = cosine_similarity(query_embedding, candidate_embedding)
    cand_blob = candidate_text(candidate)
    candidate_terms = extract_keywords(cand_blob)
    lexical = weighted_overlap(query_terms, candidate_terms)
    topic_score = topic_overlap(topic, candidate)
    title_blob = f"{candidate.get('section','')} {candidate.get('subsection','')} {candidate.get('title','')}".lower()
    exact_boost = 0.0
    if query_terms and any(term in title_blob for term in query_terms):
        exact_boost = 0.08
    if "quorum" in query_terms and "quorum" in title_blob:
        exact_boost = max(exact_boost, 0.40)
    if topic and topic in title_blob:
        exact_boost = max(exact_boost, 0.10)

    exact_boost += phrase_boost(query_lower, cand_blob)
    exact_boost = max(-0.2, min(0.40, exact_boost))
    topic_bias = section_topic_bias(query_lower, topic, candidate)

    score = (semantic * 0.40) + (lexical * 0.34) + (topic_score * 0.16) + exact_boost + topic_bias
    score = max(0.0, min(1.0, score))
    return score, {
        "semantic": semantic,
        "lexical": lexical,
        "topic": topic_score,
        "exact": exact_boost,
        "bias": topic_bias,
    }


def fetch_all_candidates(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT
                id,
                section,
                subsection,
                title,
                chapter,
                topic,
                topic_group,
                issue_category,
                keywords,
                technical_terms,
                layman_keywords,
                official_excerpt,
                normalized_legal_text,
                source_grounded_official_text,
                official_grounding_status,
                retrieval_text,
                content,
                explanation,
                plain_english,
                why_this_applies,
                real_world_example,
                common_disputes,
                example_queries,
                applicable_when,
                trigger_conditions,
                not_applicable_when,
                issue_patterns,
                recommended_next_steps,
                documents_to_collect,
                authority_to_approach,
                example,
                conditions_required,
                possible_challenges,
                related_statutes,
                embedding
            FROM bylaws
            """
        )
    ).mappings().all()
    return [dict(row) for row in rows]


def detect_clarification_needed(query: str, best_score: float, topic: str) -> tuple[bool, list[str], list[str]]:
    insight = detect_topic(query)
    meaningful_terms = [token for token in tokenize(query) if len(token) > 2 and token not in STOP_WORDS]
    low_signal = len(meaningful_terms) <= 2 or len(query.strip()) < 18
    near_tie = best_score < 0.55 and insight.is_broad
    needs_clarification = best_score < 0.40 and (low_signal or insight.is_broad) or (low_signal and near_tie)

    questions = insight.clarification_questions
    if not questions and needs_clarification:
        if topic == "agm":
            questions = ["Is this about quorum, notice, voting, minutes, or a specific resolution?"]
        elif topic == "parking":
            questions = ["Is this about allocation, visitor parking, unfair preference, or parking charges?"]
        elif topic == "maintenance":
            questions = ["Is this about bills, sinking fund use, repairs, or service charges?"]
        elif topic == "transfer":
            questions = ["Is this about share transfer, nomination, heirship, or NOC / approval delay?"]
        else:
            questions = ["Can you add the specific action, decision, or issue so the correct bye-law can be identified?"]

    possible_topics = []
    if topic == "agm":
        possible_topics = ["AGM notices", "quorum", "voting", "resolutions", "general body procedure"]
    elif topic == "parking":
        possible_topics = ["parking allocation", "visitor parking", "parking charges", "allotment policy"]
    elif topic == "maintenance":
        possible_topics = ["maintenance charges", "repairs", "sinking fund", "service charges"]
    elif topic == "transfer":
        possible_topics = ["share transfer", "nomination", "succession", "membership approval"]
    elif topic == "redevelopment":
        possible_topics = ["member consent", "developer selection", "project transparency", "conveyance"]
    elif topic == "audit":
        possible_topics = ["audit report", "books of account", "records", "rectification"]

    return needs_clarification, questions, possible_topics


def build_related_bylaws(primary: dict[str, Any], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    related = []
    primary_key = (primary.get("section"), primary.get("subsection"), primary.get("title"))
    primary_score = float(primary.get("final_score") or 0.0)

    for candidate in candidates:
        key = (candidate.get("section"), candidate.get("subsection"), candidate.get("title"))
        if key == primary_key:
            continue
        score = float(candidate.get("final_score") or 0.0)
        if score < max(0.15, primary_score - 0.30):
            continue
        related.append(
            {
                "section": candidate.get("section"),
                "subsection": candidate.get("subsection") or None,
                "title": candidate.get("title"),
                "score": round(score, 2),
                "statement": preferred_legal_text(candidate),
                "why_this_applies": candidate.get("why_this_applies") or candidate.get("plain_english") or "",
            }
        )

    related.sort(key=lambda item: item["score"], reverse=True)
    return related[:5]


def fetch_related_rules(db: Session, section: str, subsection: str | None):
    result = db.execute(
        text(
            """
            SELECT b.section,b.subsection,b.title
            FROM bylaw_relations r
            JOIN bylaws b
            ON b.section=r.target_section
            AND b.subsection=r.target_subsection
            WHERE r.source_section=:section
            AND r.source_subsection=:subsection
            LIMIT 5
            """
        ),
        {"section": section, "subsection": subsection or ""},
    )

    return [dict(row._mapping) for row in result]


def normalize_conditions(raw):
    if isinstance(raw, list):
        normalized = []
        for item in raw:
            if isinstance(item, dict):
                requirement = (
                    item.get("requirement")
                    or item.get("title")
                    or item.get("description")
                    or item.get("text")
                    or ""
                )
                plain_explanation = (
                    item.get("plain_explanation")
                    or item.get("description")
                    or item.get("text")
                    or requirement
                )
                if requirement or plain_explanation:
                    normalized.append(
                        {
                            "requirement": str(requirement).strip() or "Condition",
                            "plain_explanation": str(plain_explanation).strip()
                            or "No plain-language explanation was provided.",
                        }
                    )
            elif isinstance(item, str):
                text_value = item.strip()
                if text_value:
                    normalized.append(
                        {
                            "requirement": "Condition",
                            "plain_explanation": text_value,
                        }
                    )
        return normalized
    return []


def log_query(db: Session, description: str, best: dict[str, Any], confidence: float):
    rule = f"{best.get('section')}"
    if best.get("subsection"):
        rule += f"({best['subsection']})"
    if best.get("title"):
        rule += f" - {best['title']}"
    db.execute(
        text(
            """
            INSERT INTO query_logs(query_text,returned_rule,confidence)
            VALUES(:q,:r,:c)
            """
        ),
        {"q": description, "r": rule, "c": confidence},
    )
    db.commit()


def confidence_label(score: float, needs_clarification: bool) -> str:
    if needs_clarification:
        return "Needs Clarification"
    if score >= 0.82:
        return "Strong Match"
    if score >= 0.60:
        return "Likely Relevant"
    if score >= 0.40:
        return "Broad Topic Match"
    return "Weak Match"


def build_practical_guidance(entry: dict[str, Any]) -> str:
    steps = entry.get("recommended_next_steps") or []
    docs = entry.get("documents_to_collect") or []
    authorities = entry.get("authority_to_approach") or []
    pieces = []
    if steps:
        pieces.append("Next steps: " + "; ".join(steps[:4]))
    if docs:
        pieces.append("Documents to preserve: " + "; ".join(docs[:4]))
    if authorities:
        pieces.append("Possible authorities to approach: " + "; ".join(authorities[:3]))
    if not pieces:
        pieces.append("Keep all notices, minutes, receipts, emails, and society records before taking action.")
    return " ".join(pieces)


def preferred_legal_text(entry: dict[str, Any]) -> str:
    return (
        entry.get("source_grounded_official_text")
        or entry.get("normalized_legal_text")
        or entry.get("official_excerpt")
        or entry.get("retrieval_text")
        or entry.get("content")
        or entry.get("plain_english")
        or entry.get("why_this_applies")
        or entry.get("explanation")
        or ""
    )


def build_response(best, confidence, related_rules, related_bylaws=None, needs_clarification=False, clarification_questions=None, possible_topics=None):
    statement = preferred_legal_text(best)
    explanation = best.get("plain_english") or best.get("why_this_applies") or best.get("explanation") or statement
    practical_guidance = build_practical_guidance(best)
    when_may_not_apply = best.get("not_applicable_when") or []

    return {
        "law": LAW_NAME,
        "section": best.get("section"),
        "subsection": best.get("subsection") or None,
        "title": best.get("title"),
        "statement": statement,
        "explanation": explanation,
        "why_this_applies": best.get("why_this_applies") or explanation,
        "practical_guidance": practical_guidance,
        "citation": statement,
        "example": best.get("real_world_example") or best.get("example") or "",
        "conditions_required": normalize_conditions(best.get("conditions_required")),
        "possible_challenges": best.get("possible_challenges") or [],
        "related_statutes": best.get("related_statutes") or [],
        "related_rules": [
            {"section": r["section"], "subsection": r["subsection"] or None, "title": r["title"]}
            for r in (related_rules or [])
        ],
        "related_bylaws": related_bylaws or [],
        "confidence": round(confidence, 2),
        "confidence_label": confidence_label(confidence, needs_clarification),
        "disclaimer": DISCLAIMER_TEXT,
        "success": True,
        "message": "",
        "match_type": best.get("match_type", "semantic_match"),
        "needs_clarification": needs_clarification,
        "clarification_questions": clarification_questions or [],
        "possible_topics": possible_topics or [],
        "when_may_not_apply": when_may_not_apply or [],
        "recommended_next_steps": best.get("recommended_next_steps") or [],
        "documents_to_collect": best.get("documents_to_collect") or [],
        "possible_authorities": best.get("authority_to_approach") or [],
    }


def analyze_description(description: str, db: Session):
    start = time.perf_counter()
    try:
        return _analyze_description(description, db)
    except Exception:
        RETRIEVAL_FAILURE_COUNT.inc()
        raise
    finally:
        RETRIEVAL_LATENCY.observe(time.perf_counter() - start)


def _analyze_description(description: str, db: Session):
    ensure_query_log_table(db)

    law_ref = detect_bye_law_reference(description)
    if law_ref:
        section, subsection = law_ref
        if subsection:
            result = db.execute(
                text(
                    """
                    SELECT *
                    FROM bylaws
                    WHERE section=:section AND subsection=:subsection
                    LIMIT 1
                    """
                ),
                {"section": section, "subsection": subsection},
            ).mappings().first()
        else:
            result = db.execute(
                text(
                    """
                    SELECT *
                    FROM bylaws
                    WHERE section=:section
                    ORDER BY CASE WHEN subsection='' THEN 0 ELSE 1 END, subsection, title
                    LIMIT 1
                    """
                ),
                {"section": section},
            ).mappings().first()

        if result:
            best = dict(result)
            best["match_type"] = "exact_match"
            related = fetch_related_rules(db, section, subsection)
            related_bylaws = [
                {
                    "section": row["section"],
                    "subsection": row["subsection"] or None,
                    "title": row["title"],
                    "score": 1.0,
                    "statement": "",
                    "why_this_applies": "",
                }
                for row in related[:5]
            ]
            log_query(db, description, best, 1.0)
            return build_response(best, 1.0, related, related_bylaws=related_bylaws)

    insight = detect_topic(description)
    query_terms = expand_keywords(extract_keywords(description))
    query_embedding = get_embedding_service().encode_one(description)

    candidates = fetch_all_candidates(db)
    if not candidates:
        RETRIEVAL_FAILURE_COUNT.inc()
        return no_match_response(0.0, insight.clarification_questions)

    scored: list[dict[str, Any]] = []
    for candidate in candidates:
        score, breakdown = score_candidate(query_terms, query_embedding, candidate, insight.topic, description.lower())
        if score <= 0:
            NEGATIVE_SCORE_COUNT.inc()
        candidate = dict(candidate)
        candidate["final_score"] = score
        candidate["score_breakdown"] = breakdown
        scored.append(candidate)

    scored.sort(key=lambda item: item["final_score"], reverse=True)
    best = scored[0]
    primary_score = float(best["final_score"])
    second_score = float(scored[1]["final_score"]) if len(scored) > 1 else 0.0
    score_gap = primary_score - second_score

    needs_clarification = False
    clarification_questions: list[str] = []
    possible_topics: list[str] = []
    if primary_score < 0.45:
        needs_clarification, clarification_questions, possible_topics = detect_clarification_needed(description, primary_score, insight.topic)
    elif primary_score < 0.55 and score_gap < 0.08 and insight.is_broad:
        needs_clarification, clarification_questions, possible_topics = detect_clarification_needed(description, primary_score, insight.topic)

    related_bylaws = build_related_bylaws(best, scored)
    related_rules = [
        {"section": item["section"], "subsection": item["subsection"], "title": item["title"]}
        for item in scored[1:6]
    ]

    best["match_type"] = "likely_match" if primary_score >= 0.60 else "broad_topic_match"
    confidence = max(0.05, min(0.98, (primary_score * 0.85) + (score_gap * 0.15)))
    if needs_clarification and primary_score < 0.45:
        confidence = min(confidence, 0.55)

    if best.get("section"):
        related_from_db = fetch_related_rules(db, best["section"], best.get("subsection"))
        if related_from_db:
            related_rules = [
                {"section": row["section"], "subsection": row["subsection"] or None, "title": row["title"]}
                for row in related_from_db[:5]
            ] + related_rules
            seen = set()
            deduped = []
            for rule in related_rules:
                key = (rule["section"], rule.get("subsection"), rule["title"])
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(rule)
            related_rules = deduped[:5]

    log_query(db, description, best, confidence)
    return build_response(
        best,
        confidence,
        related_rules,
        related_bylaws=related_bylaws,
        needs_clarification=needs_clarification,
        clarification_questions=clarification_questions,
        possible_topics=possible_topics,
    )


def answer_followup(question: str, context: dict[str, Any]):
    citation = context.get("citation") or context.get("statement") or context.get("content") or ""
    if not context or not context.get("section") or not citation:
        return {
            "section": None,
            "subsection": None,
            "title": None,
            "answer": "No reliable exact bye-law match found.",
            "citation": "No reliable exact bye-law match found.",
            "confidence": 0.0,
            "disclaimer": DISCLAIMER_TEXT,
        }

    question_lower = question.lower()
    section = context.get("section")
    subsection = context.get("subsection")
    title = context.get("title")
    try:
        confidence = float(context.get("confidence") or 0.0)
    except Exception:
        confidence = 0.0

    if any(term in question_lower for term in ["text", "citation", "rule", "clause"]):
        answer = citation
    elif any(term in question_lower for term in ["challenge", "oppose", "object", "argument"]):
        challenges = context.get("possible_challenges") or []
        answer = challenges[0] if challenges else (
            "Possible objections usually depend on facts and documents, such as whether required forms, approvals, notices, dues, or committee records are complete."
        )
    elif any(term in question_lower for term in ["document", "paper", "record", "proof"]):
        docs = context.get("documents_to_collect") or []
        answer = "; ".join(docs[:5]) if docs else "Keep notices, minutes, receipts, emails, and society records."
    else:
        answer = (
            f"This follow-up is based on Bye-law {section}{f'({subsection})' if subsection else ''}: {title}. "
            "Please compare your facts with the exact clause text before relying on it."
        )

    return {
        "section": section,
        "subsection": subsection,
        "title": title,
        "answer": answer,
        "citation": citation,
        "confidence": max(0.0, min(1.0, confidence)),
        "disclaimer": DISCLAIMER_TEXT,
    }
