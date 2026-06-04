import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from retrieval_strategy import RetrievalStrategy, select_strategy
from query_understanding import detect_topic


def test_exact_citation_by_section():
    q = detect_topic("What does bye-law 25 say about parking?")
    assert select_strategy(q) == RetrievalStrategy.EXACT_CITATION


def test_keyword_semantic_for_strong_entity():
    q = detect_topic("Can society appoint expert director?")
    assert select_strategy(q) == RetrievalStrategy.KEYWORD_SEMANTIC


def test_keyword_semantic_for_subject_and_intent():
    q = detect_topic("What is quorum for AGM?")
    assert select_strategy(q) == RetrievalStrategy.KEYWORD_SEMANTIC


def test_keyword_semantic_for_actor():
    q = detect_topic("Can committee remove secretary?")
    assert select_strategy(q) == RetrievalStrategy.KEYWORD_SEMANTIC


def test_hybrid_for_vague():
    q = detect_topic("Tell me about parking rules")
    assert select_strategy(q) == RetrievalStrategy.HYBRID_RERANKER


def test_hybrid_for_short_general():
    q = detect_topic("What are the rules?")
    assert select_strategy(q) == RetrievalStrategy.HYBRID_RERANKER


def test_exact_citation_overrides_entity():
    q = detect_topic("bye-law 17(a) committee composition")
    assert select_strategy(q) == RetrievalStrategy.EXACT_CITATION


def test_keyword_semantic_focused_topic():
    q = detect_topic("Can society transfer shares to nominee?")
    assert select_strategy(q) == RetrievalStrategy.KEYWORD_SEMANTIC


def test_hybrid_for_actor_no_intent():
    q = detect_topic("Secretary rules")
    assert select_strategy(q) == RetrievalStrategy.HYBRID_RERANKER


def test_exact_section_triggers():
    s = detect_topic("What does section 12 say about maintenance?")
    assert select_strategy(s) == RetrievalStrategy.EXACT_CITATION
