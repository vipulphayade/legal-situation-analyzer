from __future__ import annotations

import math

from embeddings import EmbeddingService


def test_fallback_vector_returns_correct_dimension() -> None:
    svc = EmbeddingService()
    vec = svc._fallback_vector("quorum not met for agm meeting")
    assert len(vec) == 384
    assert all(isinstance(v, float) for v in vec)


def test_fallback_vector_is_normalized() -> None:
    svc = EmbeddingService()
    vec = svc._fallback_vector("committee refused to transfer shares")
    magnitude = math.sqrt(sum(v * v for v in vec))
    assert abs(magnitude - 1.0) < 1e-6


def test_fallback_vector_empty_text() -> None:
    svc = EmbeddingService()
    vec = svc._fallback_vector("")
    assert len(vec) == 384
    assert all(v == 0.0 for v in vec)


def test_fallback_vector_deterministic() -> None:
    svc = EmbeddingService()
    text = "parking allotment dispute with managing committee"
    v1 = svc._fallback_vector(text)
    v2 = svc._fallback_vector(text)
    assert v1 == v2


def test_fallback_encode_one() -> None:
    svc = EmbeddingService()
    vec = svc.encode_one("maintenance charges not paid")
    assert len(vec) == 384


def test_fallback_encode_batch() -> None:
    svc = EmbeddingService()
    texts = ["quorum for agm", "parking slot allotment", "sinking fund usage"]
    vectors = svc.encode(texts)
    assert len(vectors) == 3
    for vec in vectors:
        assert len(vec) == 384
