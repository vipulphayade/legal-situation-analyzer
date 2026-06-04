from __future__ import annotations

import json
import logging
import math
import re
import time
from collections import Counter
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from bylaw_seed import LAW_NAME
from embeddings import get_embedding_service
from metrics import (
    CANDIDATE_COUNT,
    CLARIFICATION_COUNT,
    FINAL_CONFIDENCE,
    MATCH_TYPE_COUNT,
    NEGATIVE_SCORE_COUNT,
    RERANKER_LATENCY,
    RETRIEVAL_FAILURE_COUNT,
    RETRIEVAL_LATENCY,
    TOP_SCORE,
)
from schemas import DISCLAIMER_TEXT
from query_understanding import QueryInsight, detect_topic
from retrieval_strategy import RetrievalStrategy, select_strategy
from reranker import rerank


logger = logging.getLogger(__name__)

RERANK_TOP_K = 20


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
    "parking": {"parking", "slot", "stilt", "vehicle", "allotment"},
    "maintenance": {"maintenance", "charges", "bill", "billing", "sinking", "fund", "repair"},
    "transfer": {"transfer", "share", "certificate", "nominee", "nomination", "heir", "successor", "sell", "sold", "sale", "noc"},
    "redevelopment": {"redevelopment", "developer", "conveyance", "project"},
    "audit": {"audit", "accounts", "books", "records", "ledger"},
    "complaint": {"complaint", "grievance", "registrar", "court", "redressal", "charity", "commissioner", "dispute"},
    "membership": {"member", "membership", "admission", "associate", "nominal"},
    "committee": {"committee", "secretary", "chairman", "management", "managing"},
    "elections": {"election", "elections", "elect", "elected", "electing", "voting", "poll", "term", "office", "bearer", "bearers"},
    "recovery": {"recovery", "recover", "recovering", "dues", "outstanding", "arrears", "unpaid", "owed", "collection"},
    "defaulters": {"defaulter", "default", "defaulted", "defaulting", "non-payment", "overdue", "delayed"},
    "property": {"property", "flat", "allotment", "possession", "exchange", "conveyance", "occupation"},
    "nomination": {"nomination", "nominee", "nominate", "nominated", "heir", "successor", "inheritance"},
    "resignation": {"resignation", "resign", "resigned"},
    "expulsion": {"expel", "expelled", "expelling", "expulsion", "nuisance", "annoyance", "inconvenience"},
    "disqualification": {"disqualify", "disqualified", "disqualification", "barred"},
    "issuance": {"issue", "issued", "issuance", "issuing"},
    "inspection": {"inspect", "inspection", "documents", "document", "copies", "copy"},
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
    "committee": {"query_tokens": {"committee", "managing", "governing", "management", "chairman", "secretary", "office", "bearer", "co-option", "disqualification", "powers", "functions"}},
    "elections": {"query_tokens": {"election", "elect", "voting", "poll", "term", "office", "bearers"}},
    "recovery": {"query_tokens": {"recovery", "dues", "outstanding", "arrears", "unpaid", "owed", "collection", "default"}},
    "defaulters": {"query_tokens": {"defaulter", "default", "non-payment", "failure", "overdue", "delayed"}},
    "property": {"query_tokens": {"property", "flat", "allotment", "possession", "exchange", "conveyance", "occupation"}},
}



# Maps detected query topics to DB topic_group values for candidate prefiltering.
# Single-group topics achieve the largest pool reduction.
# Multi-group topics catch sections split across category boundaries (e.g. committee
# sections live under both committee_governance and general_governance).
TOPIC_TO_GROUPS = {
    "agm": ["meetings_resolutions"],
    "parking": ["property_management"],
    "maintenance": ["property_management", "finance_accounts", "preliminary_general"],
    "transfer": ["membership_transfer"],
    "redevelopment": ["property_management"],
    "audit": ["finance_accounts"],
    "membership": ["membership_transfer", "preliminary_general"],
    "complaint": ["disputes_complaints"],
    "committee": ["committee_governance", "preliminary_general", "membership_transfer"],
    "elections": ["committee_governance"],
    "recovery": ["charges_fees", "preliminary_general"],
    "defaulters": ["charges_fees"],
    "property": ["property_management"],
}

# Maps detected insight topics to topic_group values for merge-level
# topic consistency checks (catches cross-topic reranker regressions).

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
    pattern = r"\b(?:bye[-\s]?law|byelaw|section)\s*(\d{1,3})\s*(?:\(?\s*([a-zA-Z]+)\s*\)?)?\b"
    match = re.search(pattern, query.lower())
    if not match:
        match = re.search(r"\b(\d{1,3})\s*\(\s*([a-zA-Z]+)\s*\)", query.lower())

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
        str(candidate.get("section") or ""),
        str(candidate.get("subsection") or ""),
        str(candidate.get("title") or ""),
        " ".join(candidate.get("keywords", []) or []),
        " ".join(candidate.get("technical_terms", []) or []),
    ]
    return " ".join(part for part in parts if part).lower()


def phrase_boost(query_lower: str, candidate_blob: str) -> float:
    boost = 0.0
    candidate_blob = candidate_blob.lower()
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
    # Concept bridge boosts for known retrieval gaps
    if any(t in query_lower for t in ["nuisance", "annoyance", "inconvenience"]):
        if "expelled" in candidate_blob or "expulsion" in candidate_blob:
            boost += 0.18
    if any(t in query_lower for t in ["inspect", "inspection", "documents", "copies"]):
        if "inspection" in candidate_blob or "records" in candidate_blob:
            boost += 0.15
    if any(t in query_lower for t in ["bearers", "office bearer"]):
        if "election" in candidate_blob or "office bearer" in candidate_blob:
            boost += 0.15
    if "sinking fund" in query_lower and any(t in query_lower for t in ["how", "calculate", "calculated", "calculation"]):
        if "break-up" in candidate_blob or ("charge" in candidate_blob and "service" in candidate_blob):
            boost += 0.25
    if any(t in query_lower for t in ["increase maintenance", "maintenance increase"]) or ("increase" in query_lower and "maintenance" in query_lower):
        if "sharing" in candidate_blob:
            boost += 0.28
    if any(t in query_lower for t in ["pay", "dues", "default", "non-payment", "outstanding", "recovery"]):
        if "overdue" in candidate_blob:
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


def _topic_overlap_single(query_topic: str, candidate_blob: str) -> float:
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
    if query_topic == "committee" and any(word in candidate_blob for word in ["committee", "managing", "chairman", "secretary", "co-opted", "disqualification"]):
        return 0.9
    if query_topic == "elections" and any(word in candidate_blob for word in ["election", "elect", "voting", "office bearer"]):
        return 0.9
    if query_topic == "recovery" and any(word in candidate_blob for word in ["recovery", "dues", "outstanding", "default", "interest", "payment", "charges"]):
        return 0.9
    if query_topic == "defaulters" and any(word in candidate_blob for word in ["default", "dues", "outstanding", "non-payment", "interest"]):
        return 0.9
    if query_topic == "property" and any(word in candidate_blob for word in ["property", "flat", "allotment", "possession", "exchange", "conveyance", "occupation"]):
        return 0.9
    return 0.0


def topic_overlap(query_topic: str, candidate: dict[str, Any], secondary_topics: list[str] | None = None) -> float:
    if not query_topic:
        return 0.0
    candidate_blob = " ".join(
        [
            str(candidate.get("topic") or ""),
            str(candidate.get("topic_group") or ""),
            str(candidate.get("chapter") or ""),
            str(candidate.get("title") or ""),
            candidate_text(candidate),
        ]
    )
    best = _topic_overlap_single(query_topic, candidate_blob)
    if secondary_topics:
        for sec_topic in secondary_topics:
            if sec_topic:
                sec_score = _topic_overlap_single(sec_topic, candidate_blob)
                if sec_score > best:
                    best = sec_score
    return best




def section_topic_bias(query_lower: str, topic: str, candidate: dict[str, Any], secondary_topics: list[str] | None = None) -> float:
    bias = _section_topic_bias_single(query_lower, topic, candidate)
    if bias != 0.0 or not secondary_topics:
        return bias
    for sec_topic in secondary_topics:
        if sec_topic and sec_topic != topic:
            sec_bias = _section_topic_bias_single(query_lower, sec_topic, candidate)
            if sec_bias != 0.0:
                return sec_bias
    return 0.0


def _section_topic_bias_single(query_lower: str, topic: str, candidate: dict[str, Any]) -> float:
    section = str(candidate.get("section") or "")

    # Penalize formation/first-general-meeting sections when query is about
    # standing committee, elected governance, or office-bearer roles.
    if topic in ("committee", "elections") and section in {"85", "86", "87", "88", "89", "90", "91", "92", "93"}:
        return -0.20
    if topic == "general" and section in {"85", "86", "87", "88", "89", "90", "91", "92", "93"}:
        committee_terms = sum(1 for t in ["committee", "election", "managing", "chairman", "secretary", "office", "bearer", "governance", "co-option"] if t in query_lower)
        if committee_terms >= 2:
            return -0.20

    if topic == "agm":
        if any(term in query_lower for term in ["quorum", "notice", "voting", "resolution", "minutes", "adjourn", "postpone"]):
            if section == "100":
                return 0.28
            if section == "101":
                return 0.18
            if section in {"98", "99"}:
                return 0.12
            if section in {"94", "95", "96", "97", "102", "103", "104", "105", "106", "107", "108", "110"}:
                return 0.06
        if "general body" in query_lower:
            if section in {"94", "95", "100", "101", "98", "99", "102", "103"}:
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
            base = 0.16
            if any(t in query_lower for t in ["application", "process", "approve", "approval", "refuse", "noc", "objection", "certificate"]):
                if "refuse" in query_lower and section == "39":
                    return base + 0.10
                if section in {"38", "39", "40"}:
                    return base + 0.06
            if any(t in query_lower for t in ["death", "nominee", "nomination", "heir", "nominate"]):
                if section in {"32", "33", "34", "35", "36", "37"}:
                    return base + 0.06
            return base
    if topic == "redevelopment":
        if section in {"154", "158", "175"}:
            return 0.22
    if topic == "audit":
        if section in {"141", "142", "143", "146", "151", "152", "153"}:
            return 0.20
    if topic == "membership":
        if section in {"16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30"}:
            return 0.14
        if section in {"49", "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60"}:
            base = 0.12
            if any(t in query_lower for t in ["nuisance", "annoyance", "ground", "grounds", "misconduct"]):
                if section == "49":
                    return 0.20
                return 0.14
            if any(t in query_lower for t in ["readmit", "readmission", "re-admit", "re-admission"]):
                if section == "55":
                    return 0.20
                return 0.14
            if any(t in query_lower for t in ["shares", "value", "interest", "acquisition"]):
                if section in {"50", "54"}:
                    return 0.18
                return 0.14
            if any(t in query_lower for t in ["procedure", "process", "how"]):
                if section == "51":
                    return 0.18
                return 0.14
            return base
    if topic == "committee":
        if section in {"111", "112", "114", "115", "116", "117", "118", "119", "120", "121", "122", "123", "124", "125", "126", "127", "128", "129", "130", "131", "132", "133", "134", "135", "136", "137", "138", "139", "140"}:
            candidate_title = str(candidate.get("title") or "").lower()
            title_overlap = sum(1 for w in set(query_lower.split()) if len(w) > 3 and w in candidate_title)
            if title_overlap >= 2:
                return 0.20
            return 0.10
    if topic == "elections":
        if section in {"115", "121", "122", "125"}:
            return 0.20
    if topic == "recovery":
        if section in {"69", "70", "71", "74"}:
            return 0.20
    if topic == "defaulters":
        if section in {"69", "70", "71"}:
            return 0.18
    if topic == "property":
        if section in {"13", "14", "24", "31", "34", "35", "38", "41", "42", "47", "61", "68", "75", "76", "154", "155", "156", "157", "158", "159", "160", "161", "167", "169", "170", "175"}:
            return 0.12
    return 0.0


def score_candidate(query_terms: set[str], query_embedding: list[float], candidate: dict[str, Any], topic: str, query_lower: str, secondary_topics: list[str] | None = None) -> tuple[float, dict[str, float]]:
    candidate_embedding = parse_embedding(candidate.get("embedding"))
    semantic = cosine_similarity(query_embedding, candidate_embedding)
    cand_blob = candidate_text(candidate)
    candidate_terms = extract_keywords(cand_blob)
    lexical = weighted_overlap(query_terms, candidate_terms)
    topic_score = topic_overlap(topic, candidate, secondary_topics)
    title_blob = f"{candidate.get('section','')} {candidate.get('subsection','')} {candidate.get('title','')}".lower()
    exact_boost = 0.0
    if query_terms and any(term in title_blob for term in query_terms):
        exact_boost = 0.08
    if "quorum" in query_terms and "quorum" in title_blob:
        exact_boost = max(exact_boost, 0.40)
    if topic and topic in title_blob:
        exact_boost = max(exact_boost, 0.10)

    legal_blob = " ".join(filter(None, [
        candidate.get("official_excerpt") or "",
        candidate.get("source_grounded_official_text") or "",
    ]))
    legal_terms = extract_keywords(legal_blob)
    legal_score = weighted_overlap(query_terms, legal_terms)

    exact_boost += phrase_boost(query_lower, cand_blob)
    exact_boost = max(-0.2, min(0.40, exact_boost))
    topic_bias = section_topic_bias(query_lower, topic, candidate, secondary_topics)

    score = (semantic * 0.40) + (lexical * 0.30) + (legal_score * 0.08) + (topic_score * 0.14) + exact_boost + topic_bias
    score = max(0.0, min(1.0, score))
    return score, {
        "semantic": semantic,
        "lexical": lexical,
        "legal": legal_score,
        "topic": topic_score,
        "exact": exact_boost,
        "bias": topic_bias,
    }


def fetch_all_candidates(db: Session, topic: str | None = None, groups: list[str] | None = None) -> list[dict[str, Any]]:
    params: dict[str, str] = {}
    if groups:
        placeholders = ", ".join(f":g{i}" for i in range(len(groups)))
        params = {f"g{i}": g for i, g in enumerate(groups)}
        where_clause = f"WHERE topic_group IN ({placeholders})"
    else:
        gs = TOPIC_TO_GROUPS.get(topic) if topic and topic != "general" else None
        if gs:
            placeholders = ", ".join(f":g{i}" for i in range(len(gs)))
            params = {f"g{i}": g for i, g in enumerate(gs)}
            where_clause = f"WHERE topic_group IN ({placeholders})"
        else:
            where_clause = ""
    rows = db.execute(
        text(
            f"""
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
                primary_retrieval_text,
                embedding
            FROM bylaws
            {where_clause}
            """
        ),
        params,
    ).mappings().all()
    return [dict(row) for row in rows]


def detect_clarification_needed(query: str, best_score: float, insight: QueryInsight) -> tuple[bool, list[str], list[str], str]:
    meaningful_terms = [token for token in tokenize(query) if len(token) > 2 and token not in STOP_WORDS]
    low_signal = len(meaningful_terms) <= 2 or len(query.strip()) < 18

    # Tiers:
    # < 0.35 — NO_MATCH, always clarify
    # 0.35-0.55 — LOW confidence, clarify
    # 0.55-0.65 — clarify only if broad, low-signal, or topic-ambiguous
    # >= 0.65 — MEDIUM/HIGH, no clarification
    clarification_message = ""
    if best_score < 0.35:
        needs_clarification = True
    elif best_score < 0.55:
        needs_clarification = True
    elif best_score < 0.65:
        # Topic ambiguity triggers within this tier: no topic matched
        # or multiple weak topics tied at score=1
        if insight.topic_score == 0:
            needs_clarification = True
            clarification_message = "Your query doesn't clearly match any specific society topic. Could you provide more detail about your issue?"
        elif insight.topic_score == 1 and len(insight.secondary_topics) >= 1:
            needs_clarification = True
            sec_topics = [st.topic for st in insight.secondary_topics]
            all_topics = [insight.topic] + sec_topics
            topic_list = ", ".join(all_topics)
            clarification_message = f"Your query could refer to multiple topics ({topic_list}). Please clarify which one applies."
        elif low_signal or insight.is_broad:
            needs_clarification = True
        else:
            needs_clarification = False
    else:
        needs_clarification = False

    questions = insight.clarification_questions
    if not questions and needs_clarification:
        if insight.topic == "agm":
            questions = ["Is this about quorum, notice, voting, minutes, or a specific resolution?"]
        elif insight.topic == "parking":
            questions = ["Is this about allocation, visitor parking, unfair preference, or parking charges?"]
        elif insight.topic == "maintenance":
            questions = ["Is this about bills, sinking fund use, repairs, or service charges?"]
        elif insight.topic == "transfer":
            questions = ["Is this about share transfer, nomination, heirship, or NOC / approval delay?"]
        elif insight.topic == "committee":
            questions = ["Is this about committee composition, meetings, powers, or disqualification of members?"]
        elif insight.topic == "elections":
            questions = ["Is this about election procedure, term of office, or voting rights?"]
        elif insight.topic == "recovery":
            questions = ["Is this about recovery of unpaid charges, interest on delayed payment, or set-off against shares?"]
        elif insight.topic == "defaulters":
            questions = ["Is this about a specific defaulter, non-payment of charges, or recovery procedure?"]
        elif insight.topic == "property":
            questions = ["Is this about flat rights, allotment, exchange, conveyance, or redevelopment?"]
        else:
            questions = ["Can you add the specific action, decision, or issue so the correct bye-law can be identified?"]

    possible_topics = []
    if insight.topic == "agm":
        possible_topics = ["AGM notices", "quorum", "voting", "resolutions", "general body procedure"]
    elif insight.topic == "parking":
        possible_topics = ["parking allocation", "visitor parking", "parking charges", "allotment policy"]
    elif insight.topic == "maintenance":
        possible_topics = ["maintenance charges", "repairs", "sinking fund", "service charges"]
    elif insight.topic == "transfer":
        possible_topics = ["share transfer", "nomination", "succession", "membership approval"]
    elif insight.topic == "redevelopment":
        possible_topics = ["member consent", "developer selection", "project transparency", "conveyance"]
    elif insight.topic == "audit":
        possible_topics = ["audit report", "books of account", "records", "rectification"]
    elif insight.topic == "committee":
        possible_topics = ["committee composition", "disqualification", "co-option", "meeting procedure", "powers of committee"]
    elif insight.topic == "elections":
        possible_topics = ["election procedure", "term of office", "voting rights", "office bearer election"]
    elif insight.topic == "recovery":
        possible_topics = ["recovery of dues", "interest on delayed payment", "set-off against shares", "default review"]
    elif insight.topic == "defaulters":
        possible_topics = ["defaulter member", "non-payment of charges", "overdue dues", "recovery procedure"]
    elif insight.topic == "property":
        possible_topics = ["flat rights", "allotment", "exchange", "conveyance", "repairs"]

    return needs_clarification, questions, possible_topics, clarification_message


def build_related_bylaws(primary: dict[str, Any], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    related: list[dict[str, Any]] = []
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

    return [dict(row) for row in result.mappings().all()]


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
    if score >= 0.80:
        return "Strong Match"
    if score >= 0.65:
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


def build_followup_questions(entry: dict[str, Any]) -> list[str]:
    questions = []
    for dispute in (entry.get("common_disputes") or [])[:3]:
        question = dispute
        if not question.endswith("?"):
            question = question + "?"
        questions.append(question)
    return questions


def build_committee_duties(entry: dict[str, Any]) -> list[str]:
    duties = []
    why = (entry.get("why_this_applies") or "").lower()
    if "committee" in why or "managing" in why or "board" in why:
        duty_keywords = ["must", "shall", "required", "responsible", "obligation", "duty"]
        if any(kw in why for kw in duty_keywords):
            duties.append(why)
    steps = entry.get("recommended_next_steps") or []
    for step in steps:
        cl = step.lower()
        if any(kw in cl for kw in ["committee", "managing", "board", "secretary", "chairman", "office bearer"]):
            duties.append(step)
    return duties[:3]


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


def build_response(best, confidence, related_rules, related_bylaws=None, needs_clarification=False, clarification_questions=None, possible_topics=None, topic="", clarification_message=""):
    statement = preferred_legal_text(best)
    explanation = best.get("plain_english") or best.get("why_this_applies") or best.get("explanation") or statement
    practical_guidance = build_practical_guidance(best)
    when_may_not_apply = best.get("not_applicable_when") or []

    result = {
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
        "clarification_message": clarification_message,
        "possible_topics": possible_topics or [],
        "when_may_not_apply": when_may_not_apply or [],
        "recommended_next_steps": best.get("recommended_next_steps") or [],
        "documents_to_collect": best.get("documents_to_collect") or [],
        "possible_authorities": best.get("authority_to_approach") or [],
    }

    # answer-layer fields (schema allows extras)
    result["applicable_bye_law"] = f"Bye-law {best.get('section')}" + (f"({best.get('subsection')})" if best.get("subsection") else "")
    result["plain_english_summary"] = best.get("plain_english") or explanation
    result["detailed_explanation"] = best.get("why_this_applies") or explanation
    result["what_you_can_do"] = best.get("recommended_next_steps") or []
    result["committee_duties"] = build_committee_duties(best)
    result["documents_to_check"] = best.get("documents_to_collect") or []
    result["suggested_questions"] = build_followup_questions(best)
    result["confidence_level"] = confidence_label(confidence, needs_clarification)
    result["common_disputes"] = best.get("common_disputes") or []

    # topic context for follow-up drift detection
    result["topic"] = topic

    return result


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
            MATCH_TYPE_COUNT.labels(match_type="exact").inc()
            FINAL_CONFIDENCE.observe(1.0)
            logger.info(json.dumps({"event": "retrieval", "path": "exact", "section": section, "subsection": subsection, "top_score": 1.0, "final_score": 1.0, "label": "Strong Match", "clarify": False}, default=str))
            return build_response(best, 1.0, related, related_bylaws=related_bylaws)

    insight = detect_topic(description)
    strategy = select_strategy(insight)
    query_terms = expand_keywords(extract_keywords(description))
    query_embedding = get_embedding_service().encode_one(description)

    # Fetch all candidates — the reranker handles noise across the full pool.
    # Topic prefilter was removed because TOPIC_TO_GROUPS mapping excluded
    # expected sections (e.g., general_governance sections for committee queries).
    candidates = fetch_all_candidates(db)
    if not candidates:
        candidates = fetch_all_candidates(db)
    CANDIDATE_COUNT.observe(len(candidates))
    if not candidates:
        RETRIEVAL_FAILURE_COUNT.inc()
        return no_match_response(0.0, insight.clarification_questions)

    scored: list[dict[str, Any]] = []
    sec_topics = [st.topic for st in insight.secondary_topics]
    for candidate in candidates:
        score, breakdown = score_candidate(query_terms, query_embedding, candidate, insight.topic, description.lower(), sec_topics)
        if score <= 0:
            NEGATIVE_SCORE_COUNT.inc()
        candidate = dict(candidate)
        candidate["final_score"] = score
        candidate["score_breakdown"] = breakdown
        scored.append(candidate)

    scored.sort(key=lambda item: item["final_score"], reverse=True)

    # Save default-scored order for reranker input, then apply strategy weights
    # on a copy so the reranker always sees the same candidate pool.
    reranker_input = scored[:RERANK_TOP_K]

    if strategy == RetrievalStrategy.KEYWORD_SEMANTIC:
        for c in scored:
            bd = c["score_breakdown"]
            c["final_score"] = (bd["semantic"] * 0.25) + (bd["lexical"] * 0.55) + (bd["topic"] * 0.12) + bd["exact"] + bd["bias"]
            c["final_score"] = max(0.0, min(1.0, c["final_score"]))
        scored.sort(key=lambda item: item["final_score"], reverse=True)

    if scored:
        TOP_SCORE.observe(float(scored[0]["final_score"]))

    # Rerank top-K with cross-encoder, then merge with heuristic order
    # to avoid regressions (reranker can hallucinate wrong sections).
    # Always rerank if enough candidates exist — strategy only affects heuristic filler weights.
    reranker_used = len(scored) >= 2
    rerank_drift = False
    if reranker_used:
        rerank_start = time.perf_counter()
        try:
            reranked = rerank(description, reranker_input, top_k=RERANK_TOP_K)
            merged = []
            seen_keys = set()
            for c in reranked:
                key = (c.get("section"), c.get("subsection"))
                if key not in seen_keys:
                    merged.append(c)
                    seen_keys.add(key)
            for c in scored:
                key = (c.get("section"), c.get("subsection"))
                if key not in seen_keys:
                    merged.append(c)
                    seen_keys.add(key)
            merged = merged[:5]
            rerank_drift = merged[0].get("section") != scored[0].get("section")
        except Exception:
            merged = scored[:5]
        RERANKER_LATENCY.observe(time.perf_counter() - rerank_start)
    else:
        merged = scored[:5]

    best = merged[0]
    primary_score = float(best["final_score"])
    second_score = float(scored[1]["final_score"]) if len(scored) > 1 else 0.0
    score_gap = primary_score - second_score

    # Consensus signal: when heuristic + reranker agree on top-1, boost confidence
    heuristic_top_section = scored[0].get("section")
    consensus_bonus = 0.08 if best.get("section") == heuristic_top_section else -0.05

    confidence = (primary_score * 0.85) + (score_gap * 0.15) + consensus_bonus
    confidence = max(0.05, min(0.98, confidence))

    needs_clarification, clarification_questions, possible_topics, clarification_message = detect_clarification_needed(
        description, primary_score, insight
    )
    CLARIFICATION_COUNT.labels(needed="true" if needs_clarification else "false").inc()
    clarification_reason = clarification_message if needs_clarification else ""
    if needs_clarification and confidence >= 0.55:
        confidence = min(confidence, 0.55)

    related_bylaws = build_related_bylaws(best, scored)
    related_rules = [
        {"section": item["section"], "subsection": item["subsection"], "title": item["title"]}
        for item in merged[1:6]
    ]

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

    best["match_type"] = "likely_match" if primary_score >= 0.60 else "broad_topic_match"
    MATCH_TYPE_COUNT.labels(match_type=best["match_type"]).inc()
    FINAL_CONFIDENCE.observe(confidence)

    logger.info(json.dumps({
        "event": "retrieval",
        "path": best["match_type"],
        "topic": insight.topic,
        "topic_score": insight.topic_score,
        "secondary_topics": [st.topic for st in insight.secondary_topics],
        "is_broad": insight.is_broad,
        "section": best.get("section"),
        "subsection": best.get("subsection"),
        "top_score": round(primary_score, 3),
        "score_gap": round(score_gap, 3),
        "final_score": round(confidence, 3),
        "label": confidence_label(confidence, needs_clarification),
        "clarify": needs_clarification,
        "clarify_reason": clarification_reason,
        "candidates": len(scored),
        "reranker": reranker_used,
        "rerank_drift": rerank_drift,
        "consensus_bonus": round(consensus_bonus, 3),
        "score_0": round(float(scored[0]["final_score"]), 3) if scored else 0,
        "score_1": round(float(scored[1]["final_score"]), 3) if len(scored) > 1 else 0,
        "score_2": round(float(scored[2]["final_score"]), 3) if len(scored) > 2 else 0,
        "breakdown_0": {k: round(v, 3) for k, v in scored[0].get("score_breakdown", {}).items()} if scored else {},
        "breakdown_1": {k: round(v, 3) for k, v in scored[1].get("score_breakdown", {}).items()} if len(scored) > 1 else {},
        "breakdown_2": {k: round(v, 3) for k, v in scored[2].get("score_breakdown", {}).items()} if len(scored) > 2 else {},
    }, default=str))

    return build_response(
        best,
        confidence,
        related_rules,
        related_bylaws=related_bylaws,
        needs_clarification=needs_clarification,
        clarification_questions=clarification_questions,
        possible_topics=possible_topics,
        topic=insight.topic,
        clarification_message=clarification_message,
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
    topic = context.get("topic", "")
    try:
        confidence = float(context.get("confidence") or 0.0)
    except Exception:
        confidence = 0.0

    # Topic drift detection — topics with common words need 2 hits, distinctive topics need 1
    topic_triggers = {
        "agm": (["agm", "annual general", "general body meeting"], 1),
        "parking": (["parking", "stilt", "visitor parking", "parking slot"], 1),
        "maintenance": (["maintenance charges", "sinking fund", "repair bill"], 2),
        "transfer": (["share transfer", "transfer certificate", "nomination"], 1),
        "redevelopment": (["redevelopment", "developer", "conveyance"], 1),
        "audit": (["audit report", "books of account", "ledger"], 1),
        "committee": (["committee composition", "co-option", "office bearer", "disqualification of members", "managing committee constituted"], 2),
        "elections": (["election", "voting", "poll", "office bearer election"], 1),
        "defaulters": (["defaulter", "non-payment", "overdue dues"], 2),
        "recovery": (["recovery of dues", "unpaid charges", "arrears"], 2),
        "property": (["property", "flat", "allotment", "conveyance deed"], 1),
    }
    if topic:
        for other_topic, (triggers, min_hits) in topic_triggers.items():
            if other_topic == topic:
                continue
            hits = sum(1 for t in triggers if t in question_lower)
            if hits >= min_hits:
                return {
                    "section": section,
                    "subsection": subsection,
                    "title": title,
                    "answer": (
                        f"This follow-up seems to be about {other_topic}, but the current "
                        f"conversation is about {topic} (Bye-law {section}). "
                        "Please run a new analysis for the new topic."
                    ),
                    "citation": citation,
                    "confidence": max(0.0, min(1.0, confidence * 0.5)),
                    "disclaimer": DISCLAIMER_TEXT,
                }

    possible_challenges = context.get("possible_challenges") or []
    documents_to_collect = context.get("documents_to_collect") or []
    recommended_steps = context.get("recommended_next_steps") or []
    why_this_applies = context.get("why_this_applies") or ""
    plain_summary = context.get("plain_english_summary") or ""
    common_disputes = context.get("common_disputes") or []

    # Branch 1: "Can they do that?" / "Is this allowed?" / "Is this legal?"
    if any(term in question_lower for term in ["can they", "is this allowed", "is this legal",
                                                "can the committee", "can the society",
                                                "do they have the right", "is it valid"]):
        parts = []
        if why_this_applies:
            parts.append(why_this_applies)
        if possible_challenges:
            parts.append("Potential issues: " + "; ".join(possible_challenges[:3]))
        if common_disputes:
            parts.append("Common disputes: " + "; ".join(common_disputes[:2]))
        answer = " ".join(parts) if parts else (
            f"Bye-law {section}{f'({subsection})' if subsection else ''} governs this. "
            "Please compare your specific facts with the official text to determine validity."
        )

    # Branch 2: "What if committee refuses?" / "What if they say no?" / "What can I do?"
    elif any(term in question_lower for term in ["what if", "what can i", "what can we",
                                                   "committee refuses", "they refuse",
                                                   "they say no", "they reject"]):
        if recommended_steps:
            answer = "You can: " + "; ".join(recommended_steps[:5])
        else:
            answer = (
                f"If the committee does not act, you may need to document the request in writing, "
                f"follow up at the next committee meeting, or approach the Registrar of Societies. "
                f"This is governed by Bye-law {section}{f'({subsection})' if subsection else ''}."
            )

    # Branch 3: "Does this need approval?" / "Who approves?" / "Who decides?"
    elif any(term in question_lower for term in ["need approval", "who approves", "who decides",
                                                   "who gives", "who authorizes", "required approval"]):
        authority = context.get("possible_authorities") or []
        if authority:
            answer = "Approval is needed from: " + "; ".join(authority[:3])
        else:
            answer = (
                f"This is governed by Bye-law {section}{f'({subsection})' if subsection else ''}: "
                f"{title}. Check whether the bye-law mentions general body approval, "
                "committee resolution, or Registrar consent."
            )

    # Branch 4: "What documents?" / "What records?" / "What proof?"
    elif any(term in question_lower for term in ["document", "paper", "record", "proof",
                                                   "receipt", "form", "application"]):
        if documents_to_collect:
            answer = "Required documents: " + "; ".join(documents_to_collect[:5])
        else:
            answer = "Keep all notices, minutes, receipts, emails, and society records."

    # Branch 5: "Tell me more" / "Explain" / "What does this mean?"
    elif any(term in question_lower for term in ["explain", "tell me more", "what does this mean",
                                                   "can you elaborate", "more details",
                                                   "what is this about"]):
        if plain_summary and why_this_applies and plain_summary != why_this_applies:
            answer = f"{plain_summary} {why_this_applies}"
        else:
            answer = plain_summary or why_this_applies or citation

    # Branch 6: "Citation" / "Rule text"
    elif any(term in question_lower for term in ["text", "citation", "rule", "clause"]):
        answer = citation

    # Branch 7: "Challenges" / "Objections"
    elif any(term in question_lower for term in ["challenge", "oppose", "object", "argument"]):
        if possible_challenges:
            answer = "Potential challenges: " + "; ".join(possible_challenges[:3])
        else:
            answer = (
                "Possible objections usually depend on facts and documents, such as whether "
                "required forms, approvals, notices, dues, or committee records are complete."
            )

    # Branch 8: related bylaw follow-up
    elif any(term in question_lower for term in ["related", "other section", "also applies",
                                                   "another byelaw", "another bye-law"]):
        related = context.get("related_bylaws") or []
        if related:
            lines = [f"{r['section']}: {r['title']}" for r in related[:5]]
            answer = "Related bye-laws: " + "; ".join(lines)
        else:
            answer = f"No related bye-laws found for section {section}."

    # Fallback
    else:
        if plain_summary:
            answer = plain_summary
        else:
            answer = (
                f"This follow-up is based on Bye-law {section}{f'({subsection})' if subsection else ''}: "
                f"{title}. Please compare your facts with the exact clause text before relying on it."
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
