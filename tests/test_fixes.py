"""Tests for small correctness fixes.

Bug 1: detect_bye_law_reference regex only matches [a-z], missing uppercase (I), (II), (A).
Bug 2: session_context includes "content" key that doesn't exist in AnalyzeResponse.
Bug 3: detect_clarification_needed calls detect_topic again despite caller already having it.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir("/app")

import re
from typing import Any
from unittest.mock import patch

import pytest

from query_understanding import QueryInsight
from search import detect_bye_law_reference, detect_clarification_needed, confidence_label
from reranker import candidate_text as reranker_candidate_text
from main import app


# ========================================================================
# Bug 1: Uppercase subsection markers in bylaw-reference regex
# ========================================================================


@pytest.mark.parametrize(
    "query, expected",
    [
        # Lowercase — still works
        ("bye-law 123(a)", ("123", "a")),
        ("section 45(b)", ("45", "b")),
        # Uppercase — was broken before fix
        ("bye-law 123(I)", ("123", "i")),
        ("section 45(II)", ("45", "ii")),
        ("byelaw 78(A)", ("78", "a")),
        ("bye law 12(B)", ("12", "b")),
        # Standard numeric — no subsection
        ("bye-law 123", ("123", "")),
        ("section 45", ("45", "")),
        # Uppercase with parenthesis variants
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
    """Verify that the session_context construction does not include 'content'.

    We check this by reading the source of the route handler and asserting
    the key list in the dict comprehension does not contain "content".
    """
    import inspect
    from main import analyze as analyze_handler

    source = inspect.getsource(analyze_handler)
    # Find the tuple of keys in the session_context dict comprehension
    match = re.search(
        r'for k in\s*\(([^)]+)\)',
        source,
    )
    assert match is not None, "Could not find session_context key list"
    keys_str = match.group(1)
    keys = [k.strip().strip("\"'") for k in keys_str.split(",")]
    assert "content" not in keys, (
        f"'content' should not be in session_context keys, found: {keys}"
    )
    # Sanity check: required keys must still be present
    for required in ("section", "citation", "confidence"):
        assert required in keys, (
            f"Required key {required!r} missing from session_context keys: {keys}"
        )


# ========================================================================
# Bug 3: Redundant detect_topic call in detect_clarification_needed
# ========================================================================


class TestDetectClarificationNeededNoRedetect:
    """detect_clarification_needed must NOT call detect_topic internally."""

    def test_does_not_reimport_detect_topic(self) -> None:
        """Patch detect_topic at the module level and verify it's not called."""
        from search import detect_clarification_needed as dcn
        import search as search_module

        # Create a mock QueryInsight
        insight = QueryInsight(
            topic="agm",
            tokens=["agm", "quorum", "not", "met"],
            is_broad=False,
            clarification_questions=[],
            topic_score=2,
        )

        original_detect = search_module.detect_topic

        call_count = 0

        def spy(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1
            return original_detect(*args, **kwargs)

        with patch.object(search_module, "detect_topic", spy):
            dcn("quorum not met for agm", 0.35, insight)
            # detect_topic should NOT be called again inside dcn
            assert call_count == 0, (
                f"detect_clarification_needed called detect_topic {call_count} time(s); "
                "should be 0 since insight is already provided"
            )

    def test_uses_passed_insight_topic_for_questions(self) -> None:
        """The fallback questions branch should use insight.topic, not a re-detected one."""
        insight = QueryInsight(
            topic="parking",
            tokens=["parking", "slot"],
            is_broad=True,
            clarification_questions=[],
            topic_score=1,
        )
        needed, questions, topics = detect_clarification_needed(
            "parking slot issue", 0.30, insight
        )
        assert needed, "Should need clarification (low score + broad)"
        assert any("parking" in q.lower() for q in questions), (
            f"Expected parking-related questions, got: {questions}"
        )

    def test_delegates_to_insight_clarification_questions_when_available(self) -> None:
        """If the insight already has clarification_questions, use those directly."""
        insight = QueryInsight(
            topic="agm",
            tokens=["agm"],
            is_broad=True,
            clarification_questions=["Is this about quorum or notice?"],
            topic_score=1,
        )
        needed, questions, topics = detect_clarification_needed(
            "agm", 0.30, insight
        )
        assert needed
        assert questions == ["Is this about quorum or notice?"], (
            "Should use pre-computed clarification questions from insight"
        )


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
    """Smoke test: the pipeline still returns valid results after all fixes."""
    resp = client.post("/analyze", json={"description": "quorum for committee meeting"})
    if resp.status_code in (500, 503):
        pytest.skip("No database available")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data.get("section") is not None
    assert "session_token" in data


def test_analyze_uppercase_section(client: Any) -> None:
    """Query with uppercase subsection marker (I) returns same result as lowercase (i)."""
    resp_upper = client.post("/analyze", json={"description": "bye-law 12(I) what is the quorum for committee"})
    resp_lower = client.post("/analyze", json={"description": "bye-law 12(i) what is the quorum for committee"})
    if resp_upper.status_code in (500, 503):
        pytest.skip("No database available")
    assert resp_upper.status_code == 200
    assert resp_lower.status_code == 200
    data_upper = resp_upper.json()
    data_lower = resp_lower.json()
    assert data_upper["section"] == data_lower["section"], (
        f"Section mismatch: upper={data_upper['section']} lower={data_lower['section']}"
    )
    assert data_upper["subsection"] == data_lower["subsection"], (
        f"Subsection mismatch: upper={data_upper['subsection']} lower={data_lower['subsection']}"
    )


# ========================================================================
# Reranker integration tests
# ========================================================================


def test_reranker_available() -> None:
    """Cross-encoder model loads without error."""
    try:
        from reranker import get_reranker
        model = get_reranker()
        assert model is not None
    except Exception:
        pytest.skip("Reranker model not available in test environment")


@pytest.mark.skipif("not config.getoption('--reranker', default=False)")
def test_reranker_reorders_candidates() -> None:
    """Reranker produces different top-1 than heuristic for a known query."""
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
    assert rerank_top != heuristic_top, (
        f"Expected reranker to reorder; both top-1 were section {heuristic_top}"
    )


def test_exact_citation_bypasses_reranker() -> None:
    """Exact citation lookup still returns the correct section regardless of reranking."""
    from database import SessionLocal
    from search import analyze_description

    db = SessionLocal()
    result = analyze_description("tell me about bye-law 126", db)
    db.close()

    assert result["success"] is True
    assert result["section"] == "126", (
        f"Expected section 126 for exact citation, got {result['section']}"
    )


def test_reranker_fallback_on_exception() -> None:
    """When reranker raises, pipeline falls back to heuristic without crashing."""
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
    """Related bylaws are still populated after reranking."""
    from database import SessionLocal
    from search import analyze_description

    db = SessionLocal()
    result = analyze_description("how is the managing committee constituted", db)
    db.close()

    assert result["success"] is True
    assert len(result.get("related_bylaws", [])) >= 1, (
        f"Expected at least 1 related bylaw, got {result.get('related_bylaws', [])}"
    )
    assert result.get("section") is not None


# ========================================================================
# Confidence threshold and clarification behavior tests
# ========================================================================


class TestConfidenceLabel:
    """confidence_label maps scores + clarify flag to correct label."""

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
    """detect_clarification_needed uses correct thresholds for each tier."""

    @pytest.fixture
    def insight(self) -> QueryInsight:
        return QueryInsight(topic="committee", tokens=[], is_broad=False, clarification_questions=[], topic_score=2)

    @pytest.fixture
    def broad_insight(self) -> QueryInsight:
        return QueryInsight(topic="committee", tokens=[], is_broad=True, clarification_questions=[], topic_score=1)

    def test_no_match_always_clarifies(self, insight: QueryInsight) -> None:
        needed, qs, _ = detect_clarification_needed("committee meeting", 0.30, insight)
        assert needed, "Score < 0.35 should always clarify"

    def test_low_confidence_clarifies(self, insight: QueryInsight) -> None:
        needed, qs, _ = detect_clarification_needed("committee meeting", 0.45, insight)
        assert needed, "Score 0.35-0.55 should clarify"

    def test_borderline_broad_clarifies(self, broad_insight: QueryInsight) -> None:
        needed, qs, _ = detect_clarification_needed("committee meeting", 0.58, broad_insight)
        assert needed, "Score 0.55-0.65 with broad topic should clarify"

    def test_borderline_tight_no_clarify(self, insight: QueryInsight) -> None:
        needed, qs, _ = detect_clarification_needed("quorum for committee meeting with interested members", 0.58, insight)
        assert not needed, "Score 0.55-0.65 with focused query should NOT clarify"

    def test_medium_confidence_no_clarify(self, insight: QueryInsight) -> None:
        needed, qs, _ = detect_clarification_needed("committee meeting", 0.70, insight)
        assert not needed, "Score >= 0.65 should not clarify"

    def test_high_confidence_no_clarify(self, insight: QueryInsight) -> None:
        needed, qs, _ = detect_clarification_needed("committee meeting", 0.90, insight)
        assert not needed, "Score >= 0.80 should not clarify"


def test_low_confidence_query_returns_low_label() -> None:
    """A vague query should not return a HIGH or MEDIUM confidence label."""
    from database import SessionLocal
    from search import analyze_description

    db = SessionLocal()
    result = analyze_description("committee issues", db)
    db.close()

    assert result["success"] is True
    label = result.get("confidence_label", "")
    assert label not in ("Strong Match", "Likely Relevant"), (
        f"Vague query should not return {label}"
    )


def test_no_match_query_returns_no_section() -> None:
    """An extremely vague query should return no match / clarification."""
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
    """candidate_text uses primary_retrieval_text + legal text fields."""

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
        """Old retrieval_text should not appear in reranker candidate text."""
        candidate = {"retrieval_text": "old text", "primary_retrieval_text": "", "source_grounded_official_text": "", "official_excerpt": ""}
        text = reranker_candidate_text(candidate)
        assert text == ""
        assert "old text" not in text
