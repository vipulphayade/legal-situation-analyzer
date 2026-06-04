# AGENTS.md

## Repository Purpose
This repository powers a legal retrieval system for Maharashtra cooperative housing society bye-laws. It is **not** a generic chatbot. The system should retrieve the most relevant bye-law first, then explain it in plain English, then offer practical guidance and only then surface clarification if needed.

## Core Architecture Rules
- Retrieval must happen before clarification.
- Clarification is additive metadata, not a replacement for retrieval results.
- Preserve primary bye-law, related bye-laws, legal summary, explanation, confidence, and guidance.
- Avoid reverting to exact-match-only behavior unless fixing a specific regression.
- Preserve frontend/backend response compatibility.

## Repository Structure
- `api/`: FastAPI backend, retrieval, reranking, schemas, embeddings, explainability, dataset checks, and orchestration.
- `frontend/`: HTML, CSS, and JavaScript UI.
- `dataset/`: canonical dataset inputs and outputs.
- `database/`: SQL initialization and database assets.
- `docker/`: Dockerfiles for the services.
- `kubernetes/`: deployment manifests.
- `docs/`: architecture and integration notes.

## Backend Conventions
- Prefer small, targeted changes in `api/search.py`, `api/hybrid_retrieval.py`, `api/reranker.py`, `api/query_understanding.py`, `api/followup_guard.py`, `api/applicability_filter.py`, and `api/schemas.py` when working on retrieval or response shape.
- Keep retrieval fields, explanation fields, and metadata fields distinct.
- Do not let clarification logic suppress valid retrieval results.
- Normalize response data at the boundary before `AnalyzeResponse(**result)`.
- Preserve confidence transparency; low confidence should still return probable matches when available.
- Keep error handling defensive around `None`, empty lists, malformed records, and embedding failures.

## Frontend Conventions
- Preserve existing element IDs and request/response contract unless the task explicitly requires a synchronized schema change.
- Render primary results even when `needs_clarification=true`.
- Treat clarification as secondary metadata.
- Use defensive rendering for nullable fields and array fields.
- Avoid page refreshes or form submission reloads.
- Keep the UI responsive and stable; do not replace the whole layout for small fixes.

## Retrieval Architecture Guidance
- Maintain hybrid retrieval: exact citation handling, keyword/topic scoring, semantic search, reranking, and drift prevention.
- Do not embed generic boilerplate or navigation text into legal vectors.
- Keep topic-group specificity strong to reduce semantic contamination.
- Related bye-laws should be shown with relevance scores, not hidden behind clarification.
- If a query is broad, surface the likely governing bye-law and show ambiguity honestly.

## Dataset Handling Rules
- Keep exact legal text separate from explanation text.
- Preserve one subsection per record where applicable.
- Do not invent summaries during ingestion.
- Keep metadata fields lean and legally relevant.
- Preserve source integrity and avoid mixing generated prose into official text.
- Run dataset sanity checks when changing ingestion, parsing, or section/subsection handling.

## Testing Expectations
- Verify exact citation lookups.
- Verify broad queries still return probable matches plus clarification metadata.
- Verify response validation against Pydantic schemas.
- Verify follow-up handling does not contaminate primary retrieval.
- Verify frontend rendering for `needs_clarification=true` payloads and nullable fields.
- Prefer targeted smoke tests over broad refactors.

## Stabilization Workflow
1. Identify the exact failure point.
2. Trace the smallest path that triggers it.
3. Fix the boundary where data shape or control flow breaks.
4. Re-run a narrow validation or syntax check.
5. Avoid unrelated cleanup unless it is required to stop the failure.

## Anti-Regression Rules
- Do not convert the system back to v5 exact-match-only behavior.
- Do not let clarification replace retrieval.
- Do not collapse distinct schema fields into one generic blob.
- Do not broaden retrieval changes beyond the issue being fixed.
- Do not rewrite unrelated files when a normalization fix is sufficient.

## Reranker Integration (Cross-encoder)
- Enabled by default in `_analyze_description()` after heuristic scoring.
- Controlled by `RERANK_TOP_K = 20` in `api/search.py`.
- Merge logic: reranker top-5 first, then heuristic top-5 fillers — non-regressive.
- Fallback: if reranker raises any `Exception`, silently falls back to heuristic-only.
- Exact citation lookups bypass reranking entirely (early return before scoring).
- Latency measured by `RERANKER_LATENCY` Prometheus histogram (key: `legal_analyzer_reranker_duration_seconds`).
- Current CPU latency: ~200-220ms per query for 20 candidates (model: `cross-encoder/ms-marco-MiniLM-L-6-v2`).
- Benchmark with reranker: Top-1 80.8%, MRR 0.8405 (+21pp / +0.147 over heuristic-only).

## Confidence Thresholds
- Confidence formula: `primary_score * 0.85 + score_gap * 0.15 + consensus_bonus`.
- Consensus bonus: +0.08 when heuristic top-1 == reranker top-1, -0.05 when they disagree.
- Labels: **Strong Match** (>= 0.80), **Likely Relevant** (>= 0.65), **Broad Topic Match** (>= 0.40), **Weak Match** (< 0.40).
- Clarification tiers:
  - `primary_score < 0.35`: NO_MATCH — always asks for clarification.
  - `0.35 <= primary_score < 0.55`: LOW — asks for clarification.
  - `0.55 <= primary_score < 0.65`: asks for clarification only if query is broad or low-signal.
  - `primary_score >= 0.65`: MEDIUM/HIGH — no clarification needed.
- The `confidence_label` field displays "Needs Clarification" when `needs_clarification=true`, overriding the numeric label.
- When `needs_clarification=true` and confidence >= 0.55, confidence is capped at 0.55 to avoid misleading high-confidence display.

## Prompting Expectations for Future Codex Tasks
- State the exact issue, the affected layer, and the desired behavior.
- Specify whether the fix is retrieval, schema, frontend rendering, ingestion, or validation.
- Ask for the smallest safe change set.
- Preserve v6 orchestration unless explicitly told otherwise.
- When uncertainty exists, prefer stable retrieval with honest ambiguity over false certainty.

