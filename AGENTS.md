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

## Prompting Expectations for Future Codex Tasks
- State the exact issue, the affected layer, and the desired behavior.
- Specify whether the fix is retrieval, schema, frontend rendering, ingestion, or validation.
- Ask for the smallest safe change set.
- Preserve v6 orchestration unless explicitly told otherwise.
- When uncertainty exists, prefer stable retrieval with honest ambiguity over false certainty.

