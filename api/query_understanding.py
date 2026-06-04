from __future__ import annotations

import re
from dataclasses import dataclass, field


TOPIC_KEYWORDS = {
    "parking": ["parking", "slot", "stilt", "vehicle", "allotment"],
    "maintenance": ["maintenance", "charges", "billing", "sinking fund", "repairs", "bill", "sinking", "repair", "fund"],
    "transfer": ["transfer", "share certificate", "nominee", "heir", "successor", "share", "certificate", "nomination", "sell", "sold", "sale", "noc"],
    "agm": ["agm", "annual general body", "general body", "quorum", "resolution", "notice", "adjourn", "postpone", "annual", "meeting"],
    "audit": ["audit", "accounts", "books of account", "ledger", "rectification", "books", "records"],
    "redevelopment": ["redevelopment", "conveyance", "deemed conveyance", "developer", "project"],
    "membership": ["membership", "member", "admission", "associate", "nominal"],
    "complaint": ["complaint", "grievance", "registrar", "court", "redressal", "charity", "commissioner", "dispute"],
    "committee": ["committee", "managing", "governing", "management", "chairman", "secretary", "office bearer", "co-option", "vacancy", "disqualification"],
    "elections": ["election", "elections", "elect", "elected", "electing", "voting", "poll", "term of office", "office bearer", "bearer", "bearers"],
    "recovery": ["recovery", "recover", "recovering", "dues", "outstanding", "arrears", "unpaid", "owed", "collection of charges", "collection"],
    "defaulters": ["defaulter", "default", "defaulted", "defaulting", "non-payment", "failure to pay", "delayed payment", "overdue", "delayed"],
    "property": ["property", "flat", "allotment", "possession", "exchange", "conveyance", "occupation"],
}

BROAD_QUERY_CLARIFIERS = {
    "agm": [
        "Is this about quorum, notice, voting, minutes, or the validity of a resolution?",
        "Was the issue about an annual general body meeting or a special general meeting?",
    ],
    "parking": [
        "Is this about allocation, visitor parking, unfair preference, or charges?",
    ],
    "maintenance": [
        "Is this about maintenance bills, sinking fund use, repairs, or service charges?",
    ],
    "transfer": [
        "Is this about transfer documents, nomination, share certificate, or approval delay?",
    ],
    "redevelopment": [
        "Is this about member consent, developer selection, tender process, or project transparency?",
    ],
    "committee": [
        "Is this about committee composition, meetings, powers, or disqualification of members?",
    ],
    "elections": [
        "Is this about election procedure, term of office, or voting rights?",
    ],
    "recovery": [
        "Is this about recovery of unpaid charges, interest on delayed payment, or set-off against shares?",
    ],
    "defaulters": [
        "Is this about a specific defaulter, non-payment of charges, or recovery procedure?",
    ],
    "property": [
        "Is this about flat rights, allotment, exchange, conveyance, or redevelopment?",
    ],
}

INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    ("permission", ["permission", "approval", "consent", "authorization", "sanction"]),
    ("prohibition", ["cannot", "can't", "not allowed", "prohibited", "restricted", "barred", "forbidden"]),
    ("eligibility", ["eligible", "qualified", "allowed to"]),
    ("obligation", ["must", "shall", "required to", "obligation", "duty", "responsibility", "mandatory"]),
    ("authority", ["authority", "power", "empowered", "entitled", "jurisdiction"]),
    ("procedure", ["procedure", "process", "how to", "steps", "method", "way to"]),
    ("remedy", ["remedy", "recourse", "appeal", "grievance", "objection"]),
    ("rights", ["right", "entitled", "do i have"]),
    ("clarification", ["what is", "meaning", "define", "explain", "clarify", "what does", "what are"]),
]

_ACTOR_KEYWORDS: list[tuple[str, list[str]]] = [
    ("society", ["society", "housing society", "cooperative society"]),
    ("committee", ["committee", "managing committee", "governing body", "board"]),
    ("member", ["member", "shareholder", "flat owner", "resident", "occupant", "owner"]),
    ("office_bearer", ["chairman", "secretary", "treasurer", "office bearer", "president"]),
    ("registrar", ["registrar", "dcpr", "assistant registrar", "deputy registrar"]),
    ("developer", ["developer", "builder", "promoter"]),
]

ACTION_KEYWORDS: list[tuple[str, list[str]]] = [
    ("appoint", ["appoint", "nominate", "co-opt", "elect", "electing", "select", "choose"]),
    ("remove", ["remove", "terminate", "expel", "dismiss", "suspend", "disqualify", "oust", "evict"]),
    ("transfer", ["transfer", "assign", "sell", "convey", "bequeath"]),
    ("recover", ["recover", "collect", "demand", "claim", "levy"]),
    ("approve", ["approve", "sanction", "authorize", "ratify", "confirm"]),
    ("hold", ["hold", "conduct", "call", "convene", "adjourn"]),
    ("change", ["change", "amend", "modify", "alter", "revise", "increase"]),
    ("challenge", ["challenge", "oppose", "object", "dispute", "appeal"]),
    ("pay", ["pay", "charge", "levy", "impose", "collect"]),
    ("vote", ["vote", "cast", "ballot", "poll"]),
    ("demand", ["demand", "ask for", "request", "require", "insist"]),
]


def _has_word(query_lower: str, word: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(word)}(?!\w)", query_lower))


def _match_first(query_lower: str, candidates: list[tuple[str, list[str]]]) -> str:
    for label, keywords in candidates:
        for keyword in keywords:
            kw_tokens = keyword.split()
            if len(kw_tokens) == 1:
                if _has_word(query_lower, keyword):
                    return label
            else:
                if keyword in query_lower:
                    return label
    return ""


def _match_first_actor(query_lower: str) -> str:
    for label, keywords in _ACTOR_KEYWORDS:
        for keyword in keywords:
            kw_tokens = keyword.split()
            if len(kw_tokens) == 1:
                if _has_word(query_lower, keyword):
                    return label
            else:
                if keyword in query_lower:
                    return label
    return ""


def _detect_intent(query_lower: str) -> str:
    intent = _match_first(query_lower, INTENT_PATTERNS)
    if intent:
        return intent
    if re.match(r"can\s", query_lower) and re.search(r"\bbecome\b", query_lower):
        return "eligibility"
    if re.match(r"can\s", query_lower) and re.search(r"\bdo\b", query_lower):
        return "remedy"
    if re.match(r"can\s", query_lower):
        return "authority"
    if re.match(r"who can\b", query_lower):
        return "eligibility"
    if re.match(r"what can\b", query_lower):
        return "remedy"
    if re.match(r"how (do|can|is|to)\b", query_lower):
        return "procedure"
    if re.match(r"what\s+(is|are|does|documents|about)\b", query_lower):
        return "clarification"
    if re.match(r"bye[-\s]?law|section\s+\d+", query_lower):
        return "clarification"
    return ""


def _extract_subject(query_lower: str, tokens: list[str]) -> str:
    subjects = [
        ("expert director", ["expert director", "professional director", "nominated director"]),
        ("parking slot", ["parking slot", "stilt parking", "visitor parking", "parking"]),
        ("share certificate", ["share certificate"]),
        ("maintenance charges", ["maintenance charges", "service charges", "maintenance bill"]),
        ("committee member", ["committee member", "mc member", "managing committee member", "committee composition"]),
        ("office bearer", ["secretary", "chairman", "treasurer", "president", "office bearer"]),
        ("quorum", ["quorum"]),
        ("resolution", ["resolution"]),
        ("meeting", ["meeting", "general body", "general meeting", "committee meeting", "agm", "adjournment"]),
        ("sinking fund", ["sinking fund", "repair fund", "reserve fund"]),
        ("redevelopment", ["redevelopment", "redevelopment project", "redevelopment plan"]),
        ("complaint", ["complaint", "grievance"]),
        ("nominee", ["nominee", "nomination", "heir", "successor"]),
        ("transfer", ["transfer"]),
        ("dues", ["dues", "outstanding", "arrears", "unpaid"]),
        ("default", ["default", "defaulter", "non-payment", "overdue"]),
        ("audit", ["audit", "audit report", "auditor", "accounts"]),
        ("bye_law_amendment", ["bye-law amendment", "bye law amendment", "amendment"]),
    ]
    query_for_subject = _strip_leading_question_words(query_lower)
    for label, keywords in subjects:
        for keyword in keywords:
            kw_tokens = keyword.split()
            if len(kw_tokens) == 1:
                if _has_word(query_for_subject, keyword):
                    return label
            else:
                if keyword in query_for_subject:
                    return label
    return ""


def _strip_leading_question_words(text: str) -> str:
    text = re.sub(r"^(what|how|can|does|do|is|are|who|where|when|why)\s+", "", text)
    text = re.sub(r"^(a|an|the|some|any)\s+", "", text)
    return text


def _detect_bye_law_reference(query: str) -> tuple[str, str] | None:
    pattern = r"\b(?:bye[-\s]?law|byelaw|section)\s*(\d{1,3})\s*(?:\(?\s*([a-zA-Z]+)\s*\)?)?\b"
    match = re.search(pattern, query.lower())
    if not match:
        match = re.search(r"\b(\d{1,3})\s*\(\s*([a-zA-Z]+)\s*\)", query.lower())
    if match:
        section = match.group(1)
        subsection = match.group(2).lower() if match.group(2) else ""
        return section, subsection
    return None


@dataclass(frozen=False)
class TopicMatch:
    topic: str = "general"
    keyword_matches: int = 0
    group: str = ""


@dataclass(frozen=True)
class QueryInsight:
    topic: str
    tokens: list[str] = field(default_factory=list)
    is_broad: bool = False
    clarification_questions: list[str] = field(default_factory=list)
    topic_score: int = 0
    intent: str = ""
    actor: str = ""
    action: str = ""
    subject: str = ""
    section_ref: str = ""
    subsection_ref: str = ""
    primary_topic: TopicMatch = field(default_factory=TopicMatch)
    secondary_topics: list[TopicMatch] = field(default_factory=list)
    topic_confidence: str = "low"


def detect_topic(query: str) -> QueryInsight:
    lowered = query.lower()
    tokens = [token for token in lowered.replace("/", " ").replace("-", " ").split() if token]
    all_topics: list[tuple[str, int]] = []

    for topic_name, keywords in TOPIC_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            kw_tokens = keyword.split()
            if len(kw_tokens) == 1:
                if _has_word(lowered, keyword):
                    score += 1
            else:
                if keyword in lowered:
                    score += 1
        if score > 0:
            all_topics.append((topic_name, score))

    all_topics.sort(key=lambda x: x[1], reverse=True)

    best_topic = "general"
    best_score = 0
    if all_topics:
        best_topic = all_topics[0][0]
        best_score = all_topics[0][1]

    # Build primary + secondary TopicMatch objects
    primary_topic = TopicMatch(topic=best_topic, keyword_matches=best_score, group=best_topic)
    secondary_topics: list[TopicMatch] = []
    for t_name, t_score in all_topics[1:]:
        secondary_topics.append(TopicMatch(topic=t_name, keyword_matches=t_score, group=t_name))

    # Confidence from Stage 8C.1.5
    topic_confidence = "high"
    if best_score == 0:
        topic_confidence = "low"
    elif best_score == 1 and len(all_topics) >= 2:
        topic_confidence = "low"
    elif best_score < 3 or (len(all_topics) >= 2 and best_score - all_topics[1][1] < 2):
        topic_confidence = "medium"

    meaningful_tokens = [token for token in tokens if len(token) > 2]
    is_broad = len(meaningful_tokens) <= 3 or best_score == 0
    clarification_questions = BROAD_QUERY_CLARIFIERS.get(best_topic, []) if is_broad else []

    intent = _detect_intent(lowered)
    actor = _match_first_actor(lowered)
    action = _match_first(lowered, ACTION_KEYWORDS)
    subject = _extract_subject(lowered, meaningful_tokens)

    law_ref = _detect_bye_law_reference(query)
    section_ref = law_ref[0] if law_ref else ""
    subsection_ref = law_ref[1] if law_ref else ""

    return QueryInsight(
        topic=best_topic,
        tokens=meaningful_tokens,
        is_broad=is_broad,
        clarification_questions=clarification_questions,
        topic_score=best_score,
        intent=intent,
        actor=actor,
        action=action,
        subject=subject,
        section_ref=section_ref,
        subsection_ref=subsection_ref,
        primary_topic=primary_topic,
        secondary_topics=secondary_topics,
        topic_confidence=topic_confidence,
    )
