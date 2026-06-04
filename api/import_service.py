from __future__ import annotations

import csv

import json
import logging
import os
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from bylaw_seed import RETRIEVAL_STOP_WORDS, build_dataset, build_relations
from embeddings import get_embedding_service


logger = logging.getLogger(__name__)


ROOT_DIR = Path(os.getenv("APP_ROOT", Path(__file__).resolve().parent))
if not (ROOT_DIR / "dataset").exists():
    ROOT_DIR = ROOT_DIR.parent

DEFAULT_DATASET_PATH = ROOT_DIR / "dataset" / "bylaws_dataset.json"

def serialize_embedding(vector: list[float]) -> str:
    rounded = [f"{value:.8f}" for value in vector]
    return "[" + ",".join(rounded) + "]"


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value).split("|") if part.strip()]


def _pick(*values: Any, default: str = "") -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return default


def _compact_terms(values: Any) -> list[str]:
    if not values:
        return []
    if not isinstance(values, list):
        values = [values]
    seen: set[str] = set()
    items: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in RETRIEVAL_STOP_WORDS:
            continue
        if lowered not in seen:
            seen.add(lowered)
            items.append(text)
    return items


def _as_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def build_retrieval_text(entry: dict[str, Any]) -> str:
    subsection = entry.get("subsection") or ""
    label = f"Bye-law {entry.get('section', '')}"
    if subsection:
        label = f"{label}({subsection})"
    parts = [
        label,
        entry.get("title", ""),
        entry.get("chapter", ""),
        entry.get("topic_group", ""),
        entry.get("official_excerpt", ""),
        entry.get("normalized_legal_text", ""),
        entry.get("source_grounded_official_text", ""),
        entry.get("normalized_text", ""),
        " ".join(_compact_terms(entry.get("keywords", []))),
        " ".join(_compact_terms(entry.get("technical_terms", []))),
    ]
    return " ".join(part for part in parts if part).strip()



def build_search_text(entry: dict[str, Any]) -> str:
    return entry.get("retrieval_text") or build_retrieval_text(entry)


def normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    subsection = entry.get("subsection") or entry.get("section_code") or entry.get("sub_section") or ""
    subsection = str(subsection).strip()
    subsection = subsection.lower() if subsection else ""

    section = str(entry.get("section") or entry.get("bylaw_number") or "").strip()
    title = entry.get("title") or entry.get("clause_title") or f"Bye-law {section}"
    chapter = entry.get("chapter") or entry.get("chapter_title") or ""

    content = _pick(
        entry.get("official_legal_text"),
        entry.get("source_grounded_official_text"),
        entry.get("normalized_text"),
        entry.get("normalized_legal_text"),
        entry.get("bye_law_summary"),
        entry.get("content"),
        entry.get("plain_english"),
        entry.get("why_this_applies"),
        entry.get("official_excerpt"),
        default="",
    )
    explanation = _pick(
        entry.get("plain_english"),
        entry.get("why_this_applies"),
        entry.get("explanation"),
        entry.get("bye_law_summary"),
        default="",
    )
    real_world_example = _pick(
        entry.get("real_world_example"),
        entry.get("example"),
        default="",
    )
    retrieval_text = _pick(
        entry.get("retrieval_text"),
        default="",
    ) or build_retrieval_text(
        {
            "section": section,
            "subsection": subsection,
            "title": title,
            "chapter": chapter,
            "topic_group": entry.get("topic_group") or entry.get("topic") or chapter or "",
            "official_excerpt": entry.get("official_excerpt") or "",
            "normalized_text": entry.get("normalized_text") or content,
            "normalized_legal_text": entry.get("normalized_legal_text") or entry.get("normalized_text") or content,
            "source_grounded_official_text": entry.get("source_grounded_official_text") or entry.get("official_legal_text") or "",
            "keywords": _as_list(entry.get("keywords")),
            "technical_terms": _as_list(entry.get("technical_terms")),
        }
    )

    normalized = {
        "law_name": entry.get("law_name", "Maharashtra Cooperative Housing Society Model Bye-laws"),
        "section": section,
        "subsection": subsection,
        "title": title,
        "chapter": chapter,
        "topic": entry.get("topic") or entry.get("topic_group") or chapter or "model bye-laws",
        "topic_group": entry.get("topic_group") or entry.get("topic") or chapter or "",
        "keywords": _as_list(entry.get("keywords")),
        "technical_terms": _as_list(entry.get("technical_terms")),
        "layman_keywords": _as_list(entry.get("layman_keywords") or entry.get("layman_terms")),
        "official_excerpt": entry.get("official_excerpt") or "",
        "normalized_text": entry.get("normalized_text") or content,
        "normalized_legal_text": entry.get("normalized_legal_text") or entry.get("normalized_text") or content,
        "source_grounded_official_text": entry.get("source_grounded_official_text") or entry.get("official_legal_text") or "",
        "official_grounding_status": entry.get("official_grounding_status") or "",
        "official_clause_reference": entry.get("official_clause_reference") or "",
        "retrieval_text": retrieval_text,
        "content": content,
        "explanation": explanation,
        "plain_english": entry.get("plain_english") or explanation,
        "why_this_applies": entry.get("why_this_applies") or entry.get("what_this_means_practically") or explanation,
        "real_world_example": real_world_example,
        "example": real_world_example,
        "conditions_required": entry.get("conditions_required") or entry.get("conditions") or [],
        "common_disputes": _as_list(entry.get("common_disputes")),
        "example_queries": _as_list(entry.get("example_queries")),
        "applicable_when": _as_list(entry.get("applicable_when")),
        "trigger_conditions": _as_list(entry.get("trigger_conditions")),
        "not_applicable_when": _as_list(entry.get("not_applicable_when")),
        "issue_patterns": _as_list(entry.get("issue_patterns")),
        "recommended_next_steps": _as_list(entry.get("recommended_next_steps")),
        "documents_to_collect": _as_list(entry.get("documents_to_collect")),
        "authority_to_approach": _as_list(entry.get("authority_to_approach")),
        "possible_challenges": _as_list(entry.get("possible_challenges")),
        "related_statutes": _as_list(entry.get("related_statutes")),
        "structured_specific_data": _as_json_object(entry.get("structured_specific_data")),
        "official_clause_reference": entry.get("official_clause_reference") or "",
        "official_grounding_status": entry.get("official_grounding_status") or "",
    }
    return normalized


def _split_pipe_list(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item.strip() for item in value if item and item.strip()]
    return [item.strip() for item in value.split("|") if item.strip()]


def _split_condition_items(value: str | list[dict] | None) -> list[dict[str, str]]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    items = []
    for raw_item in value.split("|"):
        parts = [part.strip() for part in raw_item.split("::", 1)]
        if len(parts) == 2 and parts[0] and parts[1]:
            items.append({"requirement": parts[0], "plain_explanation": parts[1]})
    return items


def load_dataset(dataset_path: str | None = None) -> list[dict[str, Any]]:
    path = Path(dataset_path) if dataset_path else DEFAULT_DATASET_PATH
    if path.exists():
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                entries = data.get("bylaws", [])
            elif isinstance(data, list):
                entries = data
            else:
                raise ValueError("Unsupported dataset structure")

            normalized: list[dict[str, Any]] = []
            seen: set[tuple[str, str, str]] = set()
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                item = normalize_entry(entry)
                key = (item["section"], item["subsection"], item["title"])
                if key in seen:
                    continue
                seen.add(key)
                normalized.append(item)
            return normalized

        if path.suffix.lower() == ".csv":
            rows: list[dict[str, Any]] = []
            seen: set[tuple[str, str, str]] = set()
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    normalized = {
                        "law_name": row.get("law_name") or "Maharashtra Cooperative Housing Society Model Bye-laws",
                        "section": row.get("section", "").strip(),
                        "subsection": (row.get("subsection") or "").strip().lower(),
                        "title": row.get("title", "").strip(),
                        "chapter": row.get("chapter", "").strip(),
                        "topic": row.get("topic", "model bye-laws").strip(),
                        "topic_group": row.get("topic_group", "").strip(),
                        "issue_category": row.get("issue_category", "").strip(),
                        "keywords": _split_pipe_list(row.get("keywords")),
                        "technical_terms": _split_pipe_list(row.get("technical_terms")),
                        "layman_keywords": _split_pipe_list(row.get("layman_keywords")),
                        "official_excerpt": row.get("official_excerpt", "").strip(),
                        "normalized_text": row.get("normalized_text", "").strip(),
                        "normalized_legal_text": row.get("normalized_legal_text", "").strip(),
                        "source_grounded_official_text": row.get("source_grounded_official_text", "").strip(),
                        "official_legal_text": row.get("official_legal_text", "").strip(),
                        "official_grounding_status": row.get("official_grounding_status", "").strip(),
                        "structured_specific_data": row.get("structured_specific_data", "").strip(),
                        "official_clause_reference": row.get("official_clause_reference", "").strip(),
                        "retrieval_text": row.get("retrieval_text", "").strip(),
                        "content": row.get("content", "").strip(),
                        "explanation": row.get("explanation", "").strip(),
                        "plain_english": row.get("plain_english", "").strip(),
                        "why_this_applies": row.get("why_this_applies", "").strip(),
                        "real_world_example": row.get("real_world_example", "").strip(),
                        "example": row.get("example", "").strip(),
                        "conditions_required": _split_condition_items(row.get("conditions_required")),
                        "common_disputes": _split_pipe_list(row.get("common_disputes")),
                        "example_queries": _split_pipe_list(row.get("example_queries")),
                        "applicable_when": _split_pipe_list(row.get("applicable_when")),
                        "trigger_conditions": _split_pipe_list(row.get("trigger_conditions")),
                        "not_applicable_when": _split_pipe_list(row.get("not_applicable_when")),
                        "issue_patterns": _split_pipe_list(row.get("issue_patterns")),
                        "recommended_next_steps": _split_pipe_list(row.get("recommended_next_steps")),
                        "documents_to_collect": _split_pipe_list(row.get("documents_to_collect")),
                        "authority_to_approach": _split_pipe_list(row.get("authority_to_approach")),
                        "possible_challenges": _split_pipe_list(row.get("possible_challenges")),
                        "related_statutes": _split_pipe_list(row.get("related_statutes")),
                        "structured_specific_data": _as_json_object(row.get("structured_specific_data")),
                        "official_clause_reference": row.get("official_clause_reference", "").strip(),
                    }
                    key = (normalized["section"], normalized["subsection"], normalized["title"])
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append(normalized)
            return rows

    logger.error("Dataset not found at %s — cannot seed the database.", path)
    raise FileNotFoundError(f"Dataset not found at {path}. Place the dataset file at {DEFAULT_DATASET_PATH} or set APP_ROOT to the project root.")


def import_dataset(
    db: Session,
    dataset_path: str | None = None,
    replace_existing: bool = False,
) -> int:
    dataset = load_dataset(dataset_path)
    relations = build_relations(dataset)
    embedder = get_embedding_service()

    if replace_existing:
        db.execute(text("TRUNCATE TABLE bylaw_relations, bylaws RESTART IDENTITY CASCADE"))
        db.commit()

    search_texts = [build_search_text(entry) for entry in dataset]
    embeddings = embedder.encode(search_texts)

    insert_sql = text(
        """
        INSERT INTO bylaws (
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
        ) VALUES (
            :section,
            :subsection,
            :title,
            :chapter,
            :topic,
            :topic_group,
            :issue_category,
            :keywords,
            :technical_terms,
            :layman_keywords,
            :official_excerpt,
            :normalized_legal_text,
            :source_grounded_official_text,
            :official_grounding_status,
            :retrieval_text,
            :content,
            :explanation,
            :plain_english,
            :why_this_applies,
            :real_world_example,
            :common_disputes,
            :example_queries,
            :applicable_when,
            :trigger_conditions,
            :not_applicable_when,
            :issue_patterns,
            :recommended_next_steps,
            :documents_to_collect,
            :authority_to_approach,
            :example,
            CAST(:conditions_required AS jsonb),
            :possible_challenges,
            :related_statutes,
            CAST(:embedding AS vector)
        )
        ON CONFLICT (section, subsection, title)
        DO UPDATE SET
            chapter = EXCLUDED.chapter,
            topic = EXCLUDED.topic,
            topic_group = EXCLUDED.topic_group,
            issue_category = EXCLUDED.issue_category,
            keywords = EXCLUDED.keywords,
            technical_terms = EXCLUDED.technical_terms,
            layman_keywords = EXCLUDED.layman_keywords,
            official_excerpt = EXCLUDED.official_excerpt,
            normalized_legal_text = EXCLUDED.normalized_legal_text,
            source_grounded_official_text = EXCLUDED.source_grounded_official_text,
            official_grounding_status = EXCLUDED.official_grounding_status,
            retrieval_text = EXCLUDED.retrieval_text,
            content = EXCLUDED.content,
            explanation = EXCLUDED.explanation,
            plain_english = EXCLUDED.plain_english,
            why_this_applies = EXCLUDED.why_this_applies,
            real_world_example = EXCLUDED.real_world_example,
            common_disputes = EXCLUDED.common_disputes,
            example_queries = EXCLUDED.example_queries,
            applicable_when = EXCLUDED.applicable_when,
            trigger_conditions = EXCLUDED.trigger_conditions,
            not_applicable_when = EXCLUDED.not_applicable_when,
            issue_patterns = EXCLUDED.issue_patterns,
            recommended_next_steps = EXCLUDED.recommended_next_steps,
            documents_to_collect = EXCLUDED.documents_to_collect,
            authority_to_approach = EXCLUDED.authority_to_approach,
            example = EXCLUDED.example,
            conditions_required = EXCLUDED.conditions_required,
            possible_challenges = EXCLUDED.possible_challenges,
            related_statutes = EXCLUDED.related_statutes,
            embedding = EXCLUDED.embedding
        """
    )

    for entry, embedding_vector in zip(dataset, embeddings):
        db.execute(
            insert_sql,
            {
                "section": entry["section"],
                "subsection": entry.get("subsection", ""),
                "title": entry["title"],
                "chapter": entry.get("chapter", ""),
                "topic": entry.get("topic", "model bye-laws"),
                "topic_group": entry.get("topic_group", ""),
                "issue_category": entry.get("issue_category", ""),
                "keywords": entry.get("keywords", []),
                "technical_terms": entry.get("technical_terms", []),
                "layman_keywords": entry.get("layman_keywords", []),
                "official_excerpt": entry.get("official_excerpt", ""),
                "normalized_text": entry.get("normalized_text", ""),
                "normalized_legal_text": entry.get("normalized_legal_text", ""),
                "source_grounded_official_text": entry.get("source_grounded_official_text", ""),
                "official_grounding_status": entry.get("official_grounding_status", ""),
                "retrieval_text": entry.get("retrieval_text", ""),
                "content": entry.get("content", ""),
                "explanation": entry.get("explanation", ""),
                "plain_english": entry.get("plain_english", ""),
                "why_this_applies": entry.get("why_this_applies", ""),
                "real_world_example": entry.get("real_world_example", ""),
                "common_disputes": entry.get("common_disputes", []),
                "example_queries": entry.get("example_queries", []),
                "applicable_when": entry.get("applicable_when", []),
                "trigger_conditions": entry.get("trigger_conditions", []),
                "not_applicable_when": entry.get("not_applicable_when", []),
                "issue_patterns": entry.get("issue_patterns", []),
                "recommended_next_steps": entry.get("recommended_next_steps", []),
                "documents_to_collect": entry.get("documents_to_collect", []),
                "authority_to_approach": entry.get("authority_to_approach", []),
                "example": entry.get("example", ""),
                "conditions_required": json.dumps(entry.get("conditions_required", [])),
                "possible_challenges": entry.get("possible_challenges", []),
                "related_statutes": entry.get("related_statutes", []),
                "embedding": serialize_embedding(embedding_vector),
            },
        )

    db.execute(text("TRUNCATE TABLE bylaw_relations RESTART IDENTITY"))
    for relation in relations:
        db.execute(
            text(
                """
                INSERT INTO bylaw_relations (
                    source_section,
                    source_subsection,
                    target_section,
                    target_subsection
                ) VALUES (
                    :source_section,
                    :source_subsection,
                    :target_section,
                    :target_subsection
                )
                """
            ),
            relation,
        )

    db.commit()
    db.execute(text("ANALYZE bylaws"))
    db.commit()
    return len(dataset)





def check_dataset_integrity(db: Session) -> dict:
    """Run a lightweight integrity check on the dataset.

    Returns a dict with keys:
      - ok (bool): True if all checks pass
      - count (int): current row count
      - missing_embeddings (int): rows without embeddings
      - message (str): human-readable summary
    """
    from dataset_verifier import verify_dataset_integrity

    minimum_expected = int(os.getenv("MINIMUM_DATASET_SIZE", "1000"))
    count = db.execute(text("SELECT COUNT(*) FROM bylaws")).scalar_one()
    missing_embeddings = db.execute(
        text("SELECT COUNT(*) FROM bylaws WHERE embedding IS NULL")
    ).scalar_one()

    structural = verify_dataset_integrity(db)

    ok = (
        count >= minimum_expected
        and missing_embeddings == 0
        and structural.get("sections_ok", True)
        and structural.get("subsections_ok", True)
    )

    messages = []
    if count < minimum_expected:
        messages.append(f"row count {count} < minimum {minimum_expected}")
    if missing_embeddings > 0:
        messages.append(f"{missing_embeddings} rows missing embeddings")
    if not structural.get("sections_ok"):
        messages.append("section verification failed")
    if not structural.get("subsections_ok"):
        messages.append("subsection verification failed")

    return {
        "ok": ok,
        "count": count,
        "missing_embeddings": missing_embeddings,
        "message": "; ".join(messages) if messages else "integrity OK",
    }


def ensure_seed_data(db: Session) -> int:
    """Verify dataset integrity and rebuild if needed.

    Default behaviour (REBUILD_DATASET_ON_STARTUP=0):
      1. Check dataset integrity.
      2. If integrity OK → return count (no rebuild).
      3. If integrity fails AND count == 0 → first startup, import dataset.
      4. If integrity fails AND REBUILD=1 → rebuild.
      5. If integrity fails AND REBUILD=0 → log warning, start anyway.
    """
    rebuild = os.getenv("REBUILD_DATASET_ON_STARTUP", "0").strip().lower() not in {"0", "false", "no"}

    integrity = check_dataset_integrity(db)

    if integrity["ok"]:
        return integrity["count"]

    if integrity["count"] == 0:
        print("[import_service] First startup detected. Importing canonical dataset.")
        return import_dataset(db, replace_existing=False)

    if rebuild:
        return import_dataset(db, replace_existing=True)

    print(
        f"[import_service] WARNING: Dataset integrity check failed ({integrity['message']}) "
        "but REBUILD_DATASET_ON_STARTUP=0, continuing with existing data."
    )
    return integrity["count"]
