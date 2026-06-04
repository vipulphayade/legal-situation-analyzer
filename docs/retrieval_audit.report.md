# Retrieval System Audit Report

**Project:** Legal Situation Analyzer — Maharashtra Cooperative Housing Society Model Bye-laws  
**Date:** 2026-06-01  
**Scope:** Architecture gap analysis (v17→v19), runtime flow mapping, retrieval benchmark evaluation  

---

## Table of Contents

1. [Retrieval Architecture Gap Analysis](#1-retrieval-architecture-gap-analysis)
2. [Runtime Flow Mapping](#2-runtime-flow-mapping)
3. [Build Evaluation Dataset & Results](#3-build-evaluation-dataset--results)
4. [Summary of Findings](#4-summary-of-findings)

---

## 1. Retrieval Architecture Gap Analysis

### 1.1 Methodology

The v17 backup directory (`v17 backup/`) contains two parallel architectures:
- **Intended modular pipeline** — 10 separate scaffold files never wired into runtime
- **Actually active pipeline** — monolithic `search.py` (822 lines) that was the real system

v19 was compared byte-for-byte against the active v17 pipeline across 12 stages.

### 1.2 Stage-by-Stage Comparison

| # | Stage | v17 Intended | v17 Active | v19 Active | Verdict |
|---|---|---|---|---|---|
| 1 | **Query Understanding** | `query_understanding.py` + `context_classifier.py` + `context_memory.py` for context-aware multi-turn detection | `query_understanding.py` only — single-turn `detect_topic()` with 8 topics, broad-query detection | Identical to v17 — same file, same 8 topics, same `QueryInsight` dataclass | **Unchanged** |
| 2 | **Sparse Retrieval** | `scoring.py` with 6-component multi-vector scoring (fts, actor, issue, procedural, scenario) | `search.py` inline: `extract_keywords` → `expand_keywords` (13 synonym groups) → `weighted_overlap` (21 TERM_WEIGHTS) → `phrase_boost` (9 phrase pairs) | Identical functions, weights, synonym groups, phrase rules | **Unchanged** |
| 3 | **Semantic Retrieval** | `embeddings.py` with `EmbeddingService`, all-MiniLM-L6-v2, CPU/CUDA, fallback hash vectors | `get_embedding_service()` singleton, `encode_one()` in pipeline, `cosine_similarity()` in `score_candidate` | Identical model, fallback, similarity function | **Unchanged** |
| 4 | **Hybrid Retrieval** | `hybrid_retrieval.py` orchestrating scoring + drift prevention + top-5 truncation | `search.py` inline `score_candidate()` formula: `semantic*0.40 + lexical*0.34 + topic_score*0.16 + exact_boost + topic_bias` | Identical formula and weights | **Unchanged** |
| 5 | **Applicability Filtering** | `applicability_filter.py` with `applicable_to_query()` returning bool + metric counter | `search.py` inline: `topic_overlap()` (scored 0.0/0.9/1.0) + `section_topic_bias()` + `detect_clarification_needed()` thresholds | Identical topic rules, bias ranges, threshold at 0.45 | **Unchanged** |
| 6 | **Negative Scoring** | `scoring.py` negative_applicability subtracts 0.40. `metrics.py` `NEGATIVE_SCORE_COUNT` | `search.py` increments `NEGATIVE_SCORE_COUNT` when `score <= 0` | Identical metric and trigger | **Unchanged** |
| 7 | **Topic Drift Prevention** | `drift_prevention.py` with `+0.25` match / `-0.30` non-match | `search.py` inline: `topic_overlap()` returning 0.0 for non-match + `section_topic_bias()` (0.06–0.30 anchored to section ranges) + `detect_clarification_needed()` | Identical logic; section-anchored bias more precise than planned generic +/- | **Unchanged** |
| 8 | **Reranking** | `reranker.py` class + `RERANKER_LATENCY` metric | `search.py` inline: `scored.sort(key=lambda item: item["final_score"], reverse=True)` | Identical single-line sort | **Unchanged** |
| 9 | **Explainability** | `explainability.py` returning 4 fields | `search.py` inline: `build_response()` + `build_practical_guidance()` + `preferred_legal_text()` + `normalize_conditions()` + `confidence_label()` | Identical 5 functions | **Unchanged** |
| 10 | **Follow-up Guard** | `followup_guard.py` (max 5, relationship validation) + `session_manager.py` (in-memory dict) + context files | `search.py` `answer_followup()` routing by keyword. Client-provided context dict | **Improved**: PostgreSQL-backed sessions (300s TTL, UUID tokens, startup cleanup). New `session_store.py`. Fallback to client context. | **Improved** |
| 11 | **Related Bylaw Retrieval** | `bylaw_seed.py` `build_relations()` generating explicit relation table | `search.py`: `fetch_related_rules()` (DB query) + `build_related_bylaws()` (score-based selection: >=0.15 or within 0.30 of primary) | Identical functions, thresholds, merge pattern | **Unchanged** |
| 12 | **Confidence Scoring** | No separate file | `confidence = (primary_score * 0.85) + (score_gap * 0.15)`, clamped 0.05–0.98. 5 labels | Identical formula, thresholds, labels | **Unchanged** |

### 1.3 Dead Code Removed (v17 → v19)

All correct removals — none were ever wired into the runtime pipeline:

| Removed File | v17 Size | Reason |
|---|---|---|
| `hybrid_retrieval.py` | 992 B | Never imported by search.py |
| `reranker.py` | 474 B | Never imported by search.py |
| `applicability_filter.py` | 464 B | Never imported by search.py |
| `followup_guard.py` | 525 B | Never imported by search.py |
| `scoring.py` | 510 B | Never imported by search.py |
| `drift_prevention.py` | 195 B | Never imported by search.py |
| `explainability.py` | 301 B | Never imported by search.py |
| `context_classifier.py` | 388 B | Never wired into any pipeline |
| `context_memory.py` | 381 B | Never wired into any pipeline |
| `cache_service.py` | 150 B | Empty scaffold |
| `session_manager.py` | 356 B | Replaced by session_store.py |

### 1.4 True Changes v17 → v19

| Change | File | Impact |
|---|---|---|
| PostgreSQL-backed sessions with TTL | `session_store.py` (new) | Sessions survive replica restarts; UUID tokens replace raw client context |
| Alembic migrations | `main.py` + `alembic/` | Structured schema versioning |
| API key authentication | `auth.py` (new) | Required X-API-Key header |
| Startup session cleanup | `main.py:94` | Expired sessions deleted on startup |
| Dataset import on first startup | `import_service.py:571-573` (fixed) | Fresh DB now imports when count==0 |
| Session context bug | `main.py:123` stores `"content"` key absent from `AnalyzeResponse` | Context silently loses data |
| Regex misses uppercase | `search.py:87` `[a-z]` only | `(I)`, `(II)`, `(A)` subsections not matched (also in v17) |

---

## 2. Runtime Flow Mapping

### 2.1 Full Function Call Trace — `POST /analyze`

```
main.py:analyze()
│
├─ verify_api_key()                                    # Auth guard
├─ analyze_description(payload.description, db)
│   │
│   ├─ search.py:analyze_description()                 #[RETRIEVAL_LATENCY timer]
│   │   └─ _analyze_description(description, db)
│   │       │
│   │       ├─ [PATH A — Exact citation]
│   │       │   detect_bye_law_reference(description)  # regex: r"\b(?:bye[-\s]?law|...)..."
│   │       │   │  (section, subsection) or None
│   │       │   │
│   │       │   ├─ db.execute(SELECT * FROM bylaws WHERE section=:s ... LIMIT 1)
│   │       │   ├─ best["match_type"] = "exact_match"
│   │       │   ├─ fetch_related_rules(db, section, subsection)   # bylaw_relations table
│   │       │   ├─ log_query(db, ...)
│   │       │   └─ build_response(best, 1.0, ...)                # returns early
│   │       │
│   │       ├─ [PATH B — Semantic/keyword]
│   │       │   │
│   │       │   ├─ detect_topic(description)                      # query_understanding.py
│   │       │   │   ├─ tokenize query
│   │       │   │   ├─ score against 8 TOPIC_KEYWORDS groups
│   │       │   │   ├─ determine is_broad (≤3 meaningful tokens OR score==0)
│   │       │   │   └─ return QueryInsight(topic, tokens, is_broad, questions)
│   │       │   │
│   │       │   ├─ extract_keywords(description)
│   │       │   │   └─ tokenize + remove stop words + length>2
│   │       │   │
│   │       │   ├─ expand_keywords(keywords)
│   │       │   │   └─ check 13 SYNONYM_GROUPS, add canonical + variants
│   │       │   │
│   │       │   ├─ get_embedding_service().encode_one(description)
│   │       │   │   └─ SentenceTransformer("all-MiniLM-L6-v2") → 384-dim vector
│   │       │   │       OR hash-based fallback
│   │       │   │
│   │       │   ├─ fetch_all_candidates(db)                      # SELECT 35 cols FROM bylaws
│   │       │   │   ↓ ALL 229 rows loaded, including embedding strings
│   │       │   │
│   │       │   ├─ FOR EACH candidate (×229):
│   │       │   │   score_candidate(query_terms, query_embedding, candidate, topic, query_lower)
│   │       │   │   │
│   │       │   │   ├─ parse_embedding(candidate["embedding"])    # str→list[float]
│   │       │   │   ├─ cosine_similarity(query, candidate)        # → semantic
│   │       │   │   ├─ candidate_text(candidate)                  # concat 13 fields
│   │       │   │   ├─ extract_keywords(candidate_blob)
│   │       │   │   ├─ weighted_overlap(query_terms, candidate_terms)  # 21 TERM_WEIGHTS
│   │       │   │   ├─ topic_overlap(topic, candidate)            # 0.0/0.9/1.0
│   │       │   │   ├─ exact_boost:                               # title match + phrase_boost()
│   │       │   │   │   ├─ any term in title → +0.08
│   │       │   │   │   ├─ "quorum" in both → max(, 0.40)
│   │       │   │   │   ├─ topic in title → max(, 0.10)
│   │       │   │   │   └─ phrase_boost(query, blob) → 9 phrase pairs
│   │       │   │   ├─ section_topic_bias(query, topic, candidate)  # hardcoded section ranges
│   │       │   │   │   → 0.06–0.30
│   │       │   │   │
│   │       │   │   └─ FINAL = semantic*0.40 + lexical*0.34 + topic_score*0.16 + boost + bias
│   │       │   │       clamped [0.0, 1.0]
│   │       │   │       IF score≤0: NEGATIVE_SCORE_COUNT.inc()
│   │       │   │
│   │       │   ├─ scored.sort(key=final_score, reverse=True)
│   │       │   ├─ best = scored[0]
│   │       │   ├─ primary_score, second_score, score_gap
│   │       │   │
│   │       │   ├─ detect_clarification_needed(description, primary_score, topic)
│   │       │   │   ├─ detect_topic(query) AGAIN (redundant — second call)
│   │       │   │   ├─ low_signal = ≤2 meaningful tokens OR len<18
│   │       │   │   ├─ near_tie = score<0.55 AND broad
│   │       │   │   └─ needs_clarification = (score<0.40 AND low/broad) OR (low AND near_tie)
│   │       │   │
│   │       │   ├─ build_related_bylaws(best, scored)             # score >= max(0.15, primary-0.30)
│   │       │   ├─ related_rules from scored[1:6]
│   │       │   ├─ match_type = "likely_match" if >=0.60 else "broad_topic_match"
│   │       │   ├─ confidence = clamp(primary*0.85 + gap*0.15, 0.05, 0.98)
│   │       │   ├─ fetch_related_rules(db, section, subsection)   # DB prepend + dedup
│   │       │   ├─ log_query(db, ...)                             # INSERT INTO query_logs
│   │       │   └─ build_response(best, confidence, ...)
│   │       │       ├─ preferred_legal_text(best)                 # 7-field priority chain
│   │       │       ├─ build_practical_guidance(best)             # steps + docs + authorities
│   │       │       ├─ normalize_conditions(conditions_required)
│   │       │       └─ return 25-field response dict
│   │       │
│   │       └─ RETURN result to analyze_description()
│   │
│   └─ [Timer end / RETRIEVAL_FAILURE_COUNT.inc() on exception]
│   └─ RETURN result dict
│
├─ Build session_context:
│   extract 9 keys from result
│   "content" ← NOT in AnalyzeResponse → silently dropped (BUG)
│
├─ session_store.create(db, session_context)
│   ├─ uuid4().hex → token
│   ├─ INSERT INTO session_store(token, data) VALUES(...)
│   └─ return token
│
├─ result["session_token"] = token
└─ AnalyzeResponse(**result) → JSON response to client
```

### 2.2 Weaknesses Identified

| # | Weakness | Location | Impact |
|---|---|---|---|
| **W1** | Exact match regex `[a-z]` misses uppercase subsections | `search.py:87` | Roman numeral subsections `(I)`, `(II)`, `(A)` silently ignored |
| **W2** | Redundant `detect_topic()` call | `_analyze_description:703` + `detect_clarification_needed:421` | Query re-tokenized and rescored against 8 keyword groups — pure waste |
| **W3** | `"content"` key absent from `AnalyzeResponse` session context | `main.py:123` | Follow-up citation retrieval silently degrades — context misses intended field |
| **W4** | Full-table scan on every query | `fetch_all_candidates():373` | All 229 rows with 35 columns fetched per request, including 384-dim embedding vectors |
| **W5** | No embedding pre-filtering | `score_candidate():342` | Cosine similarity computed against all 229 candidates in Python loop — no vector index |
| **W6** | `parse_embedding` re-parses all embeddings every request | `score_candidate():343` | Vector stored as comma-separated string; parsed to `list[float]` on every call |
| **W7** | No candidate pre-filtering by topic | `_analyze_description:703-707` | Topic is detected but not used to filter candidates; all 229 always scored |
| **W8** | Session stored for no-match responses | `main.py:118-126` | Token and empty context created even when `section=None`, `success=False` |
| **W9** | `log_query` DB write on every request | `_analyze_description:764` | Not a bug, but every request does INSERT after reads |

---

## 3. Build Evaluation Dataset & Results

### 3.1 Dataset

**File:** `tests/retrieval_benchmark.json`  
**Queries:** 99  
**Topics covered:** 15  

| Topic | Queries | Expected Ground Truth |
|---|---|---|
| AGM | 9 | Sections 94-103, 108 |
| Audit | 7 | Sections 141-153 |
| Committee | 12 | Sections 111-140 |
| Complaints | 9 | Sections 23, 49, 162-174 |
| Defaulters | 5 | Sections 69-71 |
| Elections | 5 | Sections 115, 121, 125 |
| Expert director | 1 | Sections 114, 118 |
| Maintenance | 6 | Sections 13, 65-68, 155-159 |
| Membership | 13 | Sections 17-21, 25-30, 50-55 |
| Nomination | 4 | Sections 32-37 |
| Parking | 7 | Sections 78-84 |
| Property | 1 | Sections 41-42 |
| Recovery | 5 | Sections 69-74 |
| Redevelopment | 6 | Sections 154, 158, 175 |
| Sinking fund | 2 | Sections 13-14 |
| Transfer | 7 | Sections 9-10, 38-40 |

### 3.2 Benchmark Runner

**File:** `tests/_run_benchmark.py`

The runner executes each query through the live `analyze_description()` pipeline and compares the ranked output (primary section → related_rules → related_bylaws, deduplicated) against the ground-truth `expected_sections`. Metrics computed:

- **Top-1**: Is the primary section in the expected set?
- **Top-3**: Is any expected section in the first 3 ranked?
- **Top-5**: Is any expected section in the first 5 ranked?
- **MRR**: Mean Reciprocal Rank — `1/rank` of first expected section found

### 3.3 Results

#### Overall

| Metric | Score |
|---|---|
| **Top-1** | **49.5%** (49/99) |
| **Top-3** | **68.7%** (68/99) |
| **Top-5** | **77.8%** (77/99) |
| **MRR** | **0.6009** |

| Metric | Score |
|---|---|
| Total queries | 99 |
| Errors | 0 |

#### Per-Topic Breakdown

| Topic | Queries | Top-1 | Top-3 | Top-5 | MRR |
|---|---|---|---|---|---|
| Audit | 7 | 7 | 7 | 7 | **1.0000** |
| Sinking fund | 2 | 2 | 2 | 2 | **1.0000** |
| Maintenance | 6 | 5 | 5 | 5 | **0.8333** |
| Transfer | 7 | 5 | 6 | 6 | **0.7857** |
| Redevelopment | 6 | 4 | 5 | 6 | **0.7639** |
| AGM | 9 | 5 | 6 | 8 | **0.6806** |
| Recovery | 5 | 3 | 4 | 4 | **0.6667** |
| Complaints | 9 | 5 | 6 | 8 | **0.6611** |
| Membership | 13 | 7 | 10 | 11 | **0.6308** |
| Parking | 7 | 2 | 7 | 7 | **0.6190** |
| Nomination | 4 | 1 | 4 | 4 | **0.5000** |
| Committee | 12 | 3 | 4 | 7 | **0.3639** |
| Defaulters | 5 | 0 | 2 | 2 | **0.1667** |
| Property | 1 | 0 | 0 | 0 | **0.1250** |
| Elections | 5 | 0 | 0 | 0 | **0.0286** |
| Expert director | 1 | 0 | 0 | 0 | **0.0000** |

### 3.4 Failure Pattern Analysis

**Cluster 1 — Committee/Elections/Expert director (MRR: 0.00–0.36)**

Queries about elected committees, elections, office bearers, and committee composition retrieve **formation governance sections** (88-93: first general meeting, provisional committee) because:
- The embeddings for sections 88-93 contain "committee", "election", "meeting", "office" — same terms used in queries about the standing committee
- No section-level disambiguation between "provisional committee" (formation) and "elected managing committee" (ongoing governance)
- `section_topic_bias()` does not cover sections 88-93 with negative bias for committee queries

**Cluster 2 — Defaulters (MRR: 0.167)**

Queries about recovering dues, defaulting members, and non-payment retrieve **membership sections** (17-21: eligibility, admission, membership application) because:
- The default/recovery sections (69-71) have titles that don't contain strong defaulter-specific terms
- Membership sections contain "charges of the Society" and "outstanding" — semantic overlap with defaulter queries
- `topic_overlap()` gives 0.0 because the topic "recovery"/"defaulters" doesn't match any of the 8 TOPIC_KEYWORDS groups

**Cluster 3 — No topic mapping for recovery/defaulters/property**

The 8 `TOPIC_KEYWORDS` groups don't include "recovery", "default", "dues", "exchange" — so these queries fall to `topic="general"` and `topic_score=0.0`, losing 16% of the hybrid weight.

**Cluster 4 — "notice board" query returns AGM sections**

Query "The notice board is not being updated" returns sections 98-101 (notice of general body meeting) because "notice" in `TOPIC_KEYWORDS` maps to `topic="agm"`, even though the correct section is 164 (Notice board).

---

## 4. Summary of Findings

### Architecture

- **v19 runtime is byte-for-byte identical to v17 active pipeline** across all 12 stages
- 10 modular scaffold files from v17 were correctly removed (never wired)
- Only 2 true improvements in v19: PostgreSQL-backed sessions and Alembic migrations
- 1 regression in v19: `"content"` key missing from `AnalyzeResponse` breaks session context
- 1 pre-existing bug in both versions: `[a-z]` regex misses uppercase subsection letters

### Performance

- **Overall MRR: 0.60** — the system finds the right section in top-5 for 78% of queries
- **4 of 15 topics score MRR ≥ 0.75** (Audit, Sinking fund, Maintenance, Transfer)
- **4 of 15 topics score MRR ≤ 0.17** (Elections, Expert director, Property, Defaulters)
- **No topic scores MRR = 0** (meaning every topic has at least some successful retrievals)

### Root Causes of Weak Performance

1. **Topic gap**: 8 TOPIC_KEYWORDS groups are insufficient — "recovery", "defaulters", "committee", "elections", "property" are not mapped topics, losing 16% hybrid weight
2. **Semantic contamination**: Formation sections (88-93) dominate queries about elected governance because the embedding model can't distinguish "provisional committee" from "managing committee"
3. **Full brute-force scan**: No pre-filtering, no vector index, no topic-based candidate narrowing — all 229 candidates scored on every query
4. **Redundant computation**: `detect_topic()` called twice; `parse_embedding()` re-parses all 229 vectors from string on every request

### Recommendations

| Priority | Recommendation | Impact |
|---|---|---|
| P0 | Add `recovery`, `defaulters`, `elections`, `committee`, `property` to TOPIC_KEYWORDS | Immediate 16% weight recovery for 40% of benchmark queries |
| P1 | Add section-range disambiguation in `section_topic_bias()` (e.g., negative bias for sections 88-93 when topic=committee) | Fix Committee/Elections cluster (12 queries, current MRR 0.36→0.03) |
| P2 | Pre-filter candidates by topic_group before scoring | Reduce O(229) to O(~20) per query, improve Top-1 by narrowing candidate pool |
| P3 | Fix regex `[a-z]`→`[a-zA-Z]` in `detect_bye_law_reference()` | Catch roman numeral subsections `(I)`, `(II)`, `(A)` |
| P4 | Fix `main.py:123` — remove `"content"` from session context keys | Restore follow-up citation retrieval |
| P5 | Remove redundant `detect_topic()` call in `detect_clarification_needed()` | One less embedding-free topic scan per request |
