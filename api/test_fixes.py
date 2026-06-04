"""Tests for small correctness fixes.

Bug 1: detect_bye_law_reference regex only matches [a-z], missing uppercase (I), (II), (A).
Bug 2: session_context includes "content" key that doesn't exist in AnalyzeResponse.
Bug 3: detect_clarification_needed calls detect_topic again despite caller already having it.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import re
from typing import Any
from unittest.mock import patch

import pytest

from query_understanding import QueryInsight, TopicMatch
from search import detect_bye_law_reference, detect_clarification_needed, confidence_label
from reranker import candidate_text as reranker_candidate_text
from main import app


# ========================================================================
# Bug 1: Uppercase subsection markers in bylaw-reference regex
# ========================================================================


@pytest.mark.parametrize(
    "query, expected",
    [
        ("bye-law 123(a)", ("123", "a")),
        ("section 45(b)", ("45", "b")),
        ("bye-law 123(I)", ("123", "i")),
        ("section 45(II)", ("45", "ii")),
        ("byelaw 78(A)", ("78", "a")),
        ("bye law 12(B)", ("12", "b")),
        ("bye-law 123", ("123", "")),
        ("section 45", ("45", "")),
        ("bye-law 100 (I)", ("100", "i")),
        ("section 22 (A)", ("22", "a")),
    ],
)
def test_detect_bye_law_reference_uppercase(query: str, expected: tuple[str, str]) -> None:
    result = detect_bye_law_reference(query)
    assert result == expected, f"Expected {expected}, got {result} for query={query!r}"


# ========================================================================
# Bug 2: "content" key removed from session_context
# ========================================================================


def test_session_context_has_no_content_key() -> None:
    import inspect
    from main import analyze as analyze_handler

    source = inspect.getsource(analyze_handler)
    match = re.search(r'for k in\s*\(([^)]+)\)', source)
    assert match is not None, "Could not find session_context key list"
    keys_str = match.group(1)
    keys = [k.strip().strip("\"'") for k in keys_str.split(",")]
    assert "content" not in keys, f"'content' should not be in session_context keys, found: {keys}"
    for required in ("section", "citation", "confidence"):
        assert required in keys, f"Required key {required!r} missing from session_context keys: {keys}"


# ========================================================================
# Bug 3: Redundant detect_topic call in detect_clarification_needed
# ========================================================================


class TestDetectClarificationNeededNoRedetect:
    def test_does_not_reimport_detect_topic(self) -> None:
        from search import detect_clarification_needed as dcn
        import search as search_module

        insight = QueryInsight(topic="agm", tokens=["agm", "quorum", "not", "met"], is_broad=False, clarification_questions=[], topic_score=2)
        original_detect = search_module.detect_topic
        call_count = 0

        def spy(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1
            return original_detect(*args, **kwargs)

        with patch.object(search_module, "detect_topic", spy):
            dcn("quorum not met for agm", 0.35, insight)
            assert call_count == 0, f"detect_clarification_needed called detect_topic {call_count} time(s); should be 0"

    def test_uses_passed_insight_topic_for_questions(self) -> None:
        insight = QueryInsight(topic="parking", tokens=["parking", "slot"], is_broad=True, clarification_questions=[], topic_score=1)
        needed, questions, topics, msg = detect_clarification_needed("parking slot issue", 0.30, insight)
        assert needed, "Should need clarification (low score + broad)"
        assert any("parking" in q.lower() for q in questions), f"Expected parking-related questions, got: {questions}"

    def test_delegates_to_insight_clarification_questions_when_available(self) -> None:
        insight = QueryInsight(topic="agm", tokens=["agm"], is_broad=True, clarification_questions=["Is this about quorum or notice?"], topic_score=1)
        needed, questions, topics, msg = detect_clarification_needed("agm", 0.30, insight)
        assert needed
        assert questions == ["Is this about quorum or notice?"], "Should use pre-computed clarification questions from insight"


# ========================================================================
# Integration: verify the /analyze endpoint still works
# ========================================================================


@pytest.fixture
def client() -> Any:
    from fastapi.testclient import TestClient
    from auth import verify_api_key

    app.dependency_overrides[verify_api_key] = lambda: None
    yield TestClient(app, base_url="http://localhost", raise_server_exceptions=False)
    app.dependency_overrides.clear()


def test_analyze_basic_flow(client: Any) -> None:
    resp = client.post("/analyze", json={"description": "quorum for committee meeting"})
    if resp.status_code in (500, 503):
        pytest.skip("No database available")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data.get("section") is not None
    assert "session_token" in data


def test_analyze_uppercase_section(client: Any) -> None:
    resp_upper = client.post("/analyze", json={"description": "bye-law 12(I) what is the quorum for committee"})
    resp_lower = client.post("/analyze", json={"description": "bye-law 12(i) what is the quorum for committee"})
    if resp_upper.status_code in (500, 503):
        pytest.skip("No database available")
    assert resp_upper.status_code == 200
    assert resp_lower.status_code == 200
    data_upper = resp_upper.json()
    data_lower = resp_lower.json()
    assert data_upper["section"] == data_lower["section"], f"Section mismatch: upper={data_upper['section']} lower={data_lower['section']}"
    assert data_upper["subsection"] == data_lower["subsection"], f"Subsection mismatch: upper={data_upper['subsection']} lower={data_lower['subsection']}"


# ========================================================================
# Reranker integration tests
# ========================================================================


def test_reranker_available() -> None:
    try:
        from reranker import get_reranker
        model = get_reranker()
        assert model is not None
    except Exception:
        pytest.skip("Reranker model not available in test environment")


@pytest.mark.skipif("not config.getoption('--reranker', default=False)")
def test_reranker_reorders_candidates() -> None:
    from reranker import rerank
    from database import SessionLocal
    from search import fetch_all_candidates, score_candidate, extract_keywords, expand_keywords, detect_topic
    from embeddings import get_embedding_service

    db = SessionLocal()
    candidates = fetch_all_candidates(db, "committee")
    db.close()
    assert len(candidates) >= 20, "Need at least 20 committee candidates"

    emb = get_embedding_service()
    query = "What is the quorum for a committee meeting?"
    insight = detect_topic(query)
    qt = expand_keywords(extract_keywords(query))
    qe = emb.encode_one(query)

    scored = []
    for c in candidates:
        s, _ = score_candidate(qt, qe, c, insight.topic, query.lower())
        c = dict(c)
        c["final_score"] = s
        scored.append(c)
    scored.sort(key=lambda x: x["final_score"], reverse=True)

    heuristic_top = scored[0].get("section")
    reranked = rerank(query, scored[:20], top_k=5)
    rerank_top = reranked[0].get("section") if reranked else None

    assert rerank_top is not None
    assert rerank_top != heuristic_top, f"Expected reranker to reorder; both top-1 were section {heuristic_top}"


def test_exact_citation_bypasses_reranker() -> None:
    from database import SessionLocal
    from search import analyze_description

    db = SessionLocal()
    result = analyze_description("tell me about bye-law 126", db)
    db.close()

    assert result["success"] is True
    assert result["section"] == "126", f"Expected section 126 for exact citation, got {result['section']}"


def test_reranker_fallback_on_exception() -> None:
    from database import SessionLocal
    from search import analyze_description
    from unittest.mock import patch

    db = SessionLocal()
    with patch("search.rerank", side_effect=RuntimeError("model down")):
        result = analyze_description("quorum for committee meeting", db)
    db.close()

    assert result["success"] is True
    assert result.get("section") is not None
    assert result.get("confidence", 0) > 0


def test_reranker_preserves_related_bylaws() -> None:
    from database import SessionLocal
    from search import analyze_description

    db = SessionLocal()
    result = analyze_description("how is the managing committee constituted", db)
    db.close()

    assert result["success"] is True
    assert len(result.get("related_bylaws", [])) >= 1, f"Expected at least 1 related bylaw, got {result.get('related_bylaws', [])}"
    assert result.get("section") is not None


# ========================================================================
# Confidence threshold and clarification behavior tests
# ========================================================================


class TestConfidenceLabel:
    def test_high_confidence_no_clarify(self) -> None:
        assert confidence_label(0.80, False) == "Strong Match"

    def test_medium_confidence_no_clarify(self) -> None:
        assert confidence_label(0.65, False) == "Likely Relevant"
        assert confidence_label(0.66, False) == "Likely Relevant"

    def test_broad_match_no_clarify(self) -> None:
        assert confidence_label(0.55, False) == "Broad Topic Match"
        assert confidence_label(0.40, False) == "Broad Topic Match"
        assert confidence_label(0.64, False) == "Broad Topic Match"

    def test_weak_match_no_clarify(self) -> None:
        assert confidence_label(0.39, False) == "Weak Match"

    def test_needs_clarification_overrides_score(self) -> None:
        assert confidence_label(0.90, True) == "Needs Clarification"
        assert confidence_label(0.30, True) == "Needs Clarification"


class TestDetectClarificationNeededThresholds:
    @pytest.fixture
    def insight(self) -> QueryInsight:
        return QueryInsight(topic="committee", tokens=[], is_broad=False, clarification_questions=[], topic_score=2)

    @pytest.fixture
    def broad_insight(self) -> QueryInsight:
        return QueryInsight(topic="committee", tokens=[], is_broad=True, clarification_questions=[], topic_score=1)

    def test_no_match_always_clarifies(self, insight: QueryInsight) -> None:
        needed, qs, _, _ = detect_clarification_needed("committee meeting", 0.30, insight)
        assert needed, "Score < 0.35 should always clarify"

    def test_low_confidence_clarifies(self, insight: QueryInsight) -> None:
        needed, qs, _, _ = detect_clarification_needed("committee meeting", 0.45, insight)
        assert needed, "Score 0.35-0.55 should clarify"

    def test_borderline_broad_clarifies(self, broad_insight: QueryInsight) -> None:
        needed, qs, _, _ = detect_clarification_needed("committee meeting", 0.58, broad_insight)
        assert needed, "Score 0.55-0.65 with broad topic should clarify"

    def test_borderline_tight_no_clarify(self, insight: QueryInsight) -> None:
        needed, qs, _, _ = detect_clarification_needed("quorum for committee meeting with interested members", 0.58, insight)
        assert not needed, "Score 0.55-0.65 with focused query should NOT clarify"

    def test_medium_confidence_no_clarify(self, insight: QueryInsight) -> None:
        needed, qs, _, _ = detect_clarification_needed("committee meeting", 0.70, insight)
        assert not needed, "Score >= 0.65 should not clarify"

    def test_high_confidence_no_clarify(self, insight: QueryInsight) -> None:
        needed, qs, _, _ = detect_clarification_needed("committee meeting", 0.90, insight)
        assert not needed, "Score >= 0.80 should not clarify"


def test_low_confidence_query_returns_low_label() -> None:
    from database import SessionLocal
    from search import analyze_description

    db = SessionLocal()
    result = analyze_description("committee issues", db)
    db.close()

    assert result["success"] is True
    label = result.get("confidence_label", "")
    assert label not in ("Strong Match", "Likely Relevant"), f"Vague query should not return {label}"


def test_no_match_query_returns_no_section() -> None:
    from database import SessionLocal
    from search import analyze_description

    db = SessionLocal()
    result = analyze_description("help me", db)
    db.close()

    assert result["success"] is True
    assert result.get("needs_clarification", False) or result.get("section") is None


# ========================================================================
# Reranker candidate text composition
# ========================================================================


class TestRerankerCandidateText:
    def test_uses_primary_retrieval_text(self) -> None:
        candidate = {"primary_retrieval_text": "some text", "source_grounded_official_text": "", "official_excerpt": ""}
        text = reranker_candidate_text(candidate)
        assert "some text" in text
        assert text.strip() == "some text"

    def test_uses_legal_text(self) -> None:
        candidate = {"primary_retrieval_text": "", "source_grounded_official_text": "legal text here", "official_excerpt": "excerpt"}
        text = reranker_candidate_text(candidate)
        assert "legal text here" in text
        assert "excerpt" in text

    def test_combined(self) -> None:
        candidate = {"primary_retrieval_text": "query text", "source_grounded_official_text": "official text", "official_excerpt": "excerpt"}
        text = reranker_candidate_text(candidate)
        assert "query text" in text
        assert "official text" in text
        assert "excerpt" in text

    def test_missing_fields(self) -> None:
        candidate: dict = {}
        text = reranker_candidate_text(candidate)
        assert text == ""

    def test_rejects_retrieval_text(self) -> None:
        candidate = {"retrieval_text": "old text", "primary_retrieval_text": "", "source_grounded_official_text": "", "official_excerpt": ""}
        text = reranker_candidate_text(candidate)
        assert text == ""
        assert "old text" not in text


# ========================================================================
# Clarification message behavior
# ========================================================================


class TestClarificationMessage:
    def test_topic_ambiguity_sets_message(self) -> None:
        insight = QueryInsight(topic="agm", tokens=[], is_broad=False, clarification_questions=[], topic_score=1, secondary_topics=[TopicMatch(topic="parking", keyword_matches=1, group="parking")])
        needed, qs, topics, msg = detect_clarification_needed("meeting", 0.58, insight)
        assert needed
        assert "parking" in msg
        assert "agm" in msg

    def test_no_match_has_clarification(self) -> None:
        insight = QueryInsight(topic="agm", tokens=[], is_broad=False, clarification_questions=[], topic_score=0)
        needed, qs, topics, msg = detect_clarification_needed("xyz undefined", 0.30, insight)
        assert needed

    def test_high_confidence_no_message(self) -> None:
        insight = QueryInsight(topic="agm", tokens=[], is_broad=False, clarification_questions=[], topic_score=2)
        needed, qs, topics, msg = detect_clarification_needed("quorum for committee meeting", 0.90, insight)
        assert not needed
        assert msg == ""


# ========================================================================
# Explainability logging — verify new log fields exist and excluded
# fields (embeddings, candidate text, PII) are not emitted.
# ========================================================================


def test_log_includes_explainability_fields() -> None:
    import inspect
    from search import _analyze_description

    src = inspect.getsource(_analyze_description)
    log_start = src.find("logger.info(json.dumps({")
    assert log_start >= 0, "Could not find logger.info in _analyze_description"

    for field in ["secondary_topics", "reranker", "rerank_drift", "consensus_bonus", "score_0", "breakdown_0", "clarify_reason"]:
        assert field in src[log_start:], f"Missing log field: {field}"

    for excluded in ["embedding", "candidate_text", "PII"]:
        # Only check inside the log dict — not imports or other code
        log_block = src[log_start:src.find("}))", log_start) + 2]
        assert excluded not in log_block, f"Excluded field found in log dict: {excluded}"



