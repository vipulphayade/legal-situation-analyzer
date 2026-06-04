from __future__ import annotations

import json
import os
from pathlib import Path

from import_service import (
    DEFAULT_DATASET_PATH,
    load_dataset,
    normalize_entry,
    _compact_terms,
)


def test_default_dataset_path_exists() -> None:
    assert DEFAULT_DATASET_PATH.exists(), (
        f"Expected dataset at {DEFAULT_DATASET_PATH}"
    )


def test_load_dataset_returns_list() -> None:
    dataset = load_dataset()
    assert isinstance(dataset, list)
    assert len(dataset) > 0


def test_load_dataset_has_required_fields() -> None:
    dataset = load_dataset()
    for entry in dataset:
        assert "section" in entry
        assert "subsection" in entry
        assert "title" in entry
        assert "content" in entry
        assert "explanation" in entry
        assert isinstance(entry.get("keywords"), list)
        assert isinstance(entry.get("technical_terms"), list)


def test_load_dataset_no_duplicate_keys() -> None:
    dataset = load_dataset()
    keys = [(e["section"], e["subsection"], e["title"]) for e in dataset]
    assert len(keys) == len(set(keys)), "Duplicate section/subsection/title keys found"


def test_load_dataset_missing_raises() -> None:
    """When dataset path does not exist, load_dataset raises FileNotFoundError."""
    from pathlib import Path
    import logging
    logging.disable(logging.CRITICAL)
    try:
        load_dataset(str(Path.cwd() / "_nonexistent_dataset.json"))
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError:
        pass
    finally:
        logging.disable(logging.NOTSET)


def test_normalize_entry_handles_minimal_input() -> None:
    entry = {"section": "100", "title": "Test"}
    result = normalize_entry(entry)
    assert result["section"] == "100"
    assert result["title"] == "Test"
    assert result["subsection"] == ""
    assert isinstance(result["keywords"], list)
    assert isinstance(result["technical_terms"], list)


def test_normalize_entry_multiple_field_sources() -> None:
    entry = {
        "section": "150",
        "subsection": "A",
        "title": "Audit requirements",
        "official_legal_text": "The official text here",
        "plain_english": "Simple version",
        "content": "Raw content",
    }
    result = normalize_entry(entry)
    assert result["content"] == "The official text here"
    assert result["plain_english"] == "Simple version"
    assert result["explanation"] == "Simple version"


def test_compact_terms_removes_stop_words() -> None:
    terms = _compact_terms(["the", "society", "parking", "dispute"])
    assert "the" not in terms
    assert "society" not in terms
    assert "parking" in terms
    assert "dispute" in terms


def test_compact_terms_deduplicates() -> None:
    terms = _compact_terms(["parking", "PARKING", "Parking"])
    assert len(terms) == 1


def test_compact_terms_handles_none() -> None:
    assert _compact_terms(None) == []


def test_compact_terms_handles_string() -> None:
    terms = _compact_terms("parking dispute")
    assert len(terms) >= 1
