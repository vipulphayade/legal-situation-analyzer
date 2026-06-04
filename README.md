# Legal Situation Analyzer

Hybrid retrieval system for Maharashtra Cooperative Housing Society Model Bye-laws — maps society situations to the relevant bye-law, explains the match, and provides practical guidance.

---

## What This Project Demonstrates

- **Hybrid retrieval**: multi-signal scoring combining semantic similarity, weighted keyword overlap, legal-text phrase matching, topic bias, and section-specific boosts
- **Cross-encoder reranking**: `cross-encoder/ms-marco-MiniLM-L-6-v2` re-scores top-20 candidates; merged with heuristic order so reranker regressions cannot degrade results
- **Query understanding**: 13 topic groups, 12 intent patterns, actor/action/subject extraction; confidence-gated clarification with 4 tiers
- **FastAPI backend**: 6 endpoints, Pydantic validation, SQLAlchemy connection pooling with `pool_pre_ping` + `pool_recycle`, Alembic migrations
- **PostgreSQL + pgvector**: 247-record, 57-field dataset with HNSW index; upsert-based import with schema migration
- **Docker + Kubernetes**: 5-service Docker Compose stack (API, PostgreSQL, NGINX, Prometheus, Grafana); 4 Kubernetes manifests with security contexts, health probes, SecretRefs
- **Prometheus + Grafana**: 11 metric families, provisioned dashboard, structured JSON logging with per-query breakdown
- **Security hardening**: API key auth with `secrets.compare_digest`, rate limiting (slowapi), CORS, trusted hosts, security headers, production-gated credential validation, 30s request timeout, 25s graceful drain
- **Benchmark-driven development**: 99-query benchmark suite; Top-1 75.8%, MRR 0.8095; used as regression gate

---

## Problem Statement

Housing society residents and managing committees in Maharashtra need to interpret the Model Bye-laws — 175+ legal clauses covering parking, meetings, membership transfers, maintenance funds, redevelopment, complaints, elections, and dispute resolution.

Keyword search alone fails because legal clauses use different terminology than everyday speech. Semantic search alone fails because related topics bleed into each other (a parking query should not return committee-meeting results just because both contain "meeting"). Legal retrieval requires grounded answers — the system must return the correct bye-law section, explain why it applies, and acknowledge when the query is too vague for a confident match.

This system addresses those gaps with layered retrieval: intent detection, topic prefiltering, multi-signal scoring, cross-encoder reranking, confidence-thresholded clarification, and session-aware follow-up.

---

## Architecture

```
                    ┌─────────────────────────┐
                    │     User Query (text)    │
                    └───────────┬─────────────┘
                                │
                     ┌──────────▼───────────┐
                     │   Query Understanding │
                     │  ┌─────────────────┐  │
                     │  │ Topic Detection  │  │
                     │  │ (13 groups)      │  │
                     │  │ Intent Detection  │  │
                     │  │ (12 patterns)     │  │
                     │  │ Actor / Action /  │  │
                     │  │ Subject extraction│  │
                     │  │ Section Ref Regex │  │
                     │  └─────────────────┘  │
                     └──────────┬───────────┘
                                │
                     ┌──────────▼───────────┐
                     │   Strategy Selection  │
                     │  ┌─────────────────┐  │
                     │  │ EXACT_CITATION  │──┼───→ Direct DB lookup → Response
                     │  │ if section ref   │  │
                     │  │ detected         │  │
                     │  ├─────────────────┤  │
                     │  │ KEYWORD_SEMANTIC│  │
                     │  │ if entity+intent │  │
                     │  │ or focused topic │  │
                     │  ├─────────────────┤  │
                     │  │ HYBRID_RERANKER │  │
                     │  │ default fallback │  │
                     │  └─────────────────┘  │
                     └──────────┬───────────┘
                                │
                                │ (non-exact paths)
                                ▼
                     ┌──────────────────────┐
                     │     Candidate Fetch   │
                     │  (topic-prefiltered   │
                     │   from PostgreSQL)    │
                     └──────────┬───────────┘
                                │
                     ┌──────────▼───────────┐
                     │   Heuristic Scoring   │
                     │  ┌─────────────────┐  │
                     │  │ semantic × 0.40  │  │
                     │  │ lexical × 0.30   │  │
                     │  │ legal_score ×    │  │
                     │  │   0.08           │  │
                     │  │ topic × 0.14     │  │
                     │  │ phrase_boost     │  │
                     │  │ section_bias     │  │
                     │  │ exact_bonus      │  │
                     │  └─────────────────┘  │
                     └──────────┬───────────┘
                                │
                     ┌──────────▼───────────┐
                     │   Cross-Encoder       │
                     │   Reranker            │
                     │  (top-20 candidates)  │
                     │  fallback → heuristic │
                     │  if cross-encoder     │
                     │  raises an exception  │
                     └──────────┬───────────┘
                                │
                     ┌──────────▼───────────┐
                     │   Consensus Merge     │
                     │  reranker top-5 +     │
                     │  heuristic fillers    │
                     │  consensus_bonus:     │
                     │  +0.08 if agree       │
                     │  -0.05 if disagree    │
                     └──────────┬───────────┘
                                │
                     ┌──────────▼───────────┐
                     │   Clarification Gate  │
                     │  ┌─────────────────┐  │
                     │  │ ≥ 0.65 → no     │  │
                     │  │ clarify          │  │
                     │  │ 0.55-0.65 → if  │  │
                     │  │   broad/low-     │  │
                     │  │   signal/        │  │
                     │  │   ambiguous      │  │
                     │  │ 0.35-0.55 →     │  │
                     │  │   clarify        │  │
                     │  │ < 0.35 → always  │  │
                     │  │   clarify        │  │
                     │  └─────────────────┘  │
                     └──────────┬───────────┘
                                │
                     ┌──────────▼───────────┐
                     │   Response Builder    │
                     │  section + citation   │
                     │  explanation +        │
                     │  practical guidance   │
                     │  related bylaws +     │
                     │  follow-up context    │
                     │  session token        │
                     └──────────┬───────────┘
                                │
                     ┌──────────▼───────────┐
                     │   API Response        │
                     │  (JSON, Pydantic-     │
                     │   validated)          │
                     └──────────────────────┘
```

---

## Retrieval Pipeline

### Strategy selection

The system classifies every query before retrieval:

| Strategy | Trigger | Behavior |
|---|---|---|
| `EXACT_CITATION` | `detect_bye_law_reference()` matches a section/subsection pattern | Direct DB lookup by section + subsection. Bypasses all scoring and reranking. Returns the exact bye-law with 1.0 confidence. |
| `KEYWORD_SEMANTIC` | Query has a detected entity + intent, or a focused topic (topic score ≥ 2) | Heuristic scoring weighted toward lexical overlap (semantic × 0.25, lexical × 0.55, topic × 0.12, plus exact_boost and section_bias). Reranker still runs if enough candidates exist. |
| `HYBRID_RERANKER` | Default for vague, short, or general queries | Full heuristic scoring with default weights, then cross-encoder reranks top-20, then consensus merge. |

### Scoring components

```
final_score = semantic × 0.40 + lexical × 0.30 + legal_score × 0.08 + topic × 0.14
              + phrase_boost + section_bias + exact_bonus
```

- **semantic**: cosine similarity between query embedding and candidate embedding (SentenceTransformers `all-MiniLM-L6-v2`)
- **lexical**: weighted term overlap using tuned per-term weights (quorum=6.0, notice=2.0, parking=2.5, etc.)
- **legal_score**: weighted overlap against `official_excerpt` and `source_grounded_official_text` fields
- **topic**: fuzzy match between detected query topic and candidate topic/topic_group/chapter
- **phrase_boost**: domain-specific phrase pairs (e.g., "general body" ↔ "general body", "quorum" ↔ "quorum", "sinking fund" ↔ "sinking fund")
- **section_bias**: section-specific boosts per topic (e.g., agm queries → section 100 gets +0.28, parking queries → section 78 gets +0.30)
- **exact_bonus**: +0.08 when query terms appear in the title, +0.40 when "quorum" appears in a title containing "quorum"

### Confidence formula

```
confidence = (primary_score × 0.85) + (score_gap × 0.15) + consensus_bonus
```

Where `consensus_bonus` = +0.08 when heuristic top-1 matches reranker top-1, −0.05 when they disagree. Confidence is clamped to [0.05, 0.98].

### Clarification tiers

| Range | Behavior |
|---|---|
| < 0.35 | Always request clarification (NO_MATCH) |
| 0.35–0.55 | Always request clarification (LOW confidence) |
| 0.55–0.65 | Request clarification only if query is broad, low-signal, or topic-ambiguous |
| ≥ 0.65 | No clarification necessary |

---

## Key Engineering Decisions

**Hybrid retrieval over pure semantic search** — Legal text has precise terminology. Semantic search alone cannot distinguish "meeting" as committee meeting vs. general body meeting. Adding weighted keyword scoring, phrase matching, and section-specific bias anchors results to the correct jurisdiction.

**Cross-encoder reranking with consensus merging** — The bi-encoder embedding is fast but loses nuance. The cross-encoder is more accurate but adds ~200ms CPU latency. Merging reranker top-5 with heuristic fillers prevents reranker regressions from degrading results. If the cross-encoder fails (model download error, OOM), the system falls back to heuristic-only scoring.

**4-tier clarification instead of a single threshold** — Legal queries are often underspecified ("tell me about parking"). A single threshold either clarifies too often (annoying) or not often enough (unsafe). Four tiers with conditional middle-tier logic (topic ambiguity, signal strength, secondary topics) balances precision with user experience.

**Confidence scoring with consensus bonus** — The confidence formula uses both the primary score and the gap between top-1 and top-2. The consensus bonus rewards agreement between the heuristic pass and the reranker, penalizes disagreement. This produces more reliable confidence estimates than either signal alone.

**Benchmark-driven development** — The 99-query benchmark with locked results serves as the regression gate. Any retrieval change must maintain or improve Top-1 (75.8%) and MRR (0.8095) against the same suite before being safe to merge. This prevents the silent degradation that plagues many retrieval systems.

**Production hardening before deployment** — Auth, rate limiting, timeout middleware, graceful shutdown, credential validation, and observability were added before any production deployment. The self-audit (`PRODUCTION_READINESS_AUDIT.md`) documents 40+ identified gaps with staged fix priorities — none of which are hidden.

---

## Benchmark Results

Verified against 99 queries on Docker + PostgreSQL + cross-encoder reranker:

| Metric | Value |
|---|---|
| Top-1 accuracy | 75.8% |
| Top-3 accuracy | 81.8% |
| Top-5 accuracy | 92.9% |
| Mean Reciprocal Rank (MRR) | 0.8095 |
| Errors | 0 |

The benchmark serves as the project's regression gate. Any change to the retrieval logic must maintain or improve these numbers against the same 99-query suite. Benchmark queries cover all topic groups and include both exact-citation lookups and broad semantic queries.

---

## Security & Production Hardening

| Control | Implementation | Notes |
|---|---|---|
| API key authentication | `X-API-Key` header, verified via `secrets.compare_digest()` | Dev mode: disabled with warning. Production: **fails closed** with 503 if missing |
| Fail-closed production auth | `verify_api_key()` returns 503 when `PRODUCTION=1` and `API_KEY` is unset | Double-gated: startup validation + per-request auth guard |
| Audit logging | Structured `AUDIT` events emitted for auth success/failure, validation errors, oversized requests, unhandled exceptions | Separate `audit` logger; events include event type, detail, and request path |
| Request body size limit | `RequestBodySizeMiddleware`, configurable `MAX_REQUEST_BODY_SIZE` (default 64KB) | Returns 413 with clear message on oversized payloads |
| Secret redaction | No full request body logged in validation errors; `str(exc)` truncated to 200 chars; DB credentials never logged; `.env` excluded from Docker build context | |
| Rate limiting | `slowapi`, configurable default 20/minute | Respects `X-Forwarded-For` for proxy environments |
| CORS | Configurable `API_ALLOWED_ORIGINS` | Default restricts to `localhost:8080` |
| Trusted hosts | Configurable `ALLOWED_HOSTS` allowlist | Default: `localhost,127.0.0.1,api,frontend` |
| Security headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Cache-Control`, `Permissions-Policy` | Applied via middleware on every response |
| Input validation | Pydantic schemas with min/max length, custom validators | `description`: 10–3000 chars, `question`: 2–1500 chars, `session_token`: alphanumeric, max 128 chars |
| Error response sanitization | Validation errors return generic `"Invalid request body."` — no Pydantic error details leaked to client | Full details kept in server logs only |
| Request timeout | Configurable default 30s | Returns 504 on timeout |
| Graceful shutdown | 25-second drain | Waits for active requests, logs progress, then closes DB connections |
| DB connection pool | `pool_pre_ping`, `pool_recycle=3600`, size 10, overflow 10, timeout 30s | Pool metrics reported every 15s via daemon thread |
| Production validation | `PRODUCTION=1` env var | Fails startup on missing/placeholder `API_KEY` or `DB_PASSWORD` |
| Dependency scanning | `scripts/scan-dependencies.py` wraps `pip-audit` for local vulnerability scanning | Requires `pip install pip-audit` |
| Docker build safety | `.dockerignore` excludes `.env` and `.env.local` | Prevents secrets from being baked into Docker image layers |

**Remaining acknowledged gaps**: Credentials in `.env` are placeholders (must be changed for deployment); no CSRF protection (API uses token auth, not cookies); deprecated `context` field in follow-up requests still accepted for legacy frontend compatibility. Full gap audit with fix priorities: `PRODUCTION_READINESS_AUDIT.md`.

---

## Observability

### Prometheus metrics (11 metric families)

| Metric | Type | What it tracks |
|---|---|---|
| `legal_analyzer_api_requests_total` | Counter | Request count by method, path, status |
| `legal_analyzer_api_request_duration_seconds` | Histogram | API latency distribution |
| `legal_analyzer_retrieval_duration_seconds` | Histogram | Retrieval pipeline latency |
| `legal_analyzer_reranker_duration_seconds` | Histogram | Cross-encoder latency |
| `legal_analyzer_db_pool` | Gauge | Pool size / checked-in / overflow (15s interval) |
| `legal_analyzer_negative_score_total` | Counter | Candidates with non-positive scores |
| `legal_analyzer_retrieval_failures_total` | Counter | Failed or no-match retrievals |
| `legal_analyzer_candidate_count` | Histogram | Candidate pool size distribution |
| `legal_analyzer_top_score` | Histogram | Best heuristic score before reranking |
| `legal_analyzer_final_confidence` | Histogram | Final confidence returned to client |
| `legal_analyzer_clarification_total` | Counter | Clarification needed vs. not |

Latency buckets tuned for retrieval workloads: 0.01s to 30.0s.

### Structured logging

Every retrieval logs a JSON object with 20+ fields: section, subsection, topic, topic_score, secondary_topics, is_broad, top_score, score_gap, final_score, confidence label, clarify status, clarify reason, candidate count, reranker usage, rerank_drift flag, consensus_bonus, and per-candidate score breakdowns. This enables debugging retrieval quality without reproducing the exact query.

### Health checks

`/health` verifies DB connectivity with `SELECT 1`. Used by Docker Compose dependency conditions and Kubernetes probes.

---

## Infrastructure

### Docker Compose (primary)

```
docker compose up --build
```

| Service | Image | Port | Depends on |
|---|---|---|---|
| `db` | PostgreSQL 16 + pgvector | — | — |
| `api` | Python 3.12 + FastAPI | `:8000` | `db` healthy |
| `frontend` | NGINX 1.27 | `:8080` | `api` healthy |
| `prometheus` | prom/prometheus v2.55.1 | `:9090` | `api` healthy |
| `grafana` | grafana/grafana-oss v11.3.0 | `:3000` | prometheus started |

### Kubernetes

4 standalone manifests in `kubernetes/`:
- `api-deployment.yaml` — 2 replicas, readiness/liveness probes, security context (runAsNonRoot, seccomp, capability drops), CPU/memory limits, SecretRef for credentials
- `frontend-deployment.yaml` — NGINX serving both legacy and React frontends
- `postgres-deployment.yaml` — PostgreSQL + pgvector StatefulSet
- `app-secret.yaml` — Secret template (not committed with real values)

Not currently connected to CI/CD. Ready for manual `kubectl apply -f kubernetes/`.

### Frontend

Two frontends served side-by-side via NGINX:
- `/` — Legacy static HTML/CSS/JS UI
- `/modern/` — React 19 + TypeScript + Vite + Tailwind + shadcn/ui SPA

---

## Dataset

- **247 records, 57 fields** — Maharashtra Cooperative Housing Society Model Bye-laws
- Fields include: `section`, `subsection`, `title`, `chapter`, `topic`, `topic_group`, `keywords`, `technical_terms`, `official_excerpt`, `normalized_legal_text`, `source_grounded_official_text`, `retrieval_text`, `plain_english`, `why_this_applies`, `real_world_example`, `common_disputes`, `conditions_required`
- Startup validation runs 5 sanity checks: section continuity, subsection gaps, duplicates, missing text, missing embeddings
- Configurable `MINIMUM_DATASET_SIZE` and `REBUILD_DATASET_ON_STARTUP` env vars
- Import pipeline supports JSON and CSV, with dedup, upsert, and schema migration via `ALTER TABLE ADD COLUMN IF NOT EXISTS`

---

## Testing

| File | Tests | Focus |
|---|---|---|
| `test_import.py` | 14 | Dataset import, field extraction, fallback behavior |
| `test_fixes.py` | 43 | Regex, confidence labels, clarification tiers, reranker integration |
| `test_auth.py` | 1 | API key rejection |
| `test_health.py` | 1 | Health endpoint DB connectivity |
| `test_embeddings.py` | 2 | Embedding model loading |
| `test_session.py` | 1 | Session context key verification |

**74 total tests**: 60 pass locally, 6 require PostgreSQL, 8 skipped without `--reranker` flag.

---

## Known Limitations

- Cross-encoder adds ~200–220ms CPU latency per query (`cross-encoder/ms-marco-MiniLM-L-6-v2`). Acceptable for the current 247-record dataset but will increase with dataset size.
- 6 tests require a running PostgreSQL database (no mock DB for CI).
- Dataset covers Maharashtra Model Bye-laws only. Individual society bye-laws may differ.
- The HNSW index on embeddings exists in the schema but is not used at runtime — `fetch_all_candidates()` performs a full table scan with Python-side cosine similarity. At 247 rows the difference is negligible, but this does not scale beyond low thousands.
- Three separate topic/keyword definitions exist across `search.py`, `query_understanding.py`, and `bylaw_seed.py`. Adding a new topic requires updating all three.
- Kubernetes manifests are standalone (not wired to CI/CD or Helm).
- Follow-up session context expires after 5 minutes (hardcoded).
- Deprecated `context` field in follow-up requests still accepted for legacy frontend compatibility. Should be removed after frontend migration.
- Duplicate dataset copies exist (`api/bylaws_dataset.json` and `database/bylaws_dataset.json` vs. canonical `dataset/bylaws_dataset.json`). The `api/` copy has minor version skew.
- Full self-audit with staged fix priorities: `PRODUCTION_READINESS_AUDIT.md`.

---

## Future Work

- **Stratified benchmark suite**: Organize the 99-query benchmark by topic group for per-topic regression detection
- **Automated CI benchmark gate**: Run benchmark on every retrieval PR; fail if Top-1 or MRR drops below locked baseline
- **Expanded query-understanding coverage**: Add topic groups for financial governance, dispute resolution, member rights
- **Dataset augmentation pipeline**: Formalize scraped-HTML → extracted verbatim → dataset merge into a repeatable, versioned workflow with diff review
- **Reranker model evaluation**: Benchmark alternative cross-encoder models against the 99-query suite
- **HNSW index adoption**: Add ANN query path with fallback to brute-force; document trade-off
- **Consolidate topic definitions**: Merge `search.py`, `query_understanding.py`, and `bylaw_seed.py` keyword sets into a single config module
- **Production readiness automation**: Convert `PRODUCTION_READINESS_AUDIT.md` into a runnable startup assertion

---

## Repository Structure

```
legal-situation-analyzer/
├── api/                   # FastAPI backend (15 modules)
├── dataset/               # Canonical 247-record, 57-field dataset
├── database/              # PostgreSQL + pgvector init schema
├── docker/                # Dockerfiles (api, database, frontend)
├── frontend/              # Legacy static UI
├── frontend-modern/       # React 19 + TypeScript SPA
├── scripts/               # 53 dataset extraction and analysis tools
├── tests/                 # Benchmark suites and test files
├── alembic/               # Database migrations
├── prometheus/            # Prometheus configuration
├── grafana/               # Provisioned dashboards and datasource
├── kubernetes/            # Deployment manifests (4 files)
├── docs/                  # Architecture notes, audit reports
├── docker-compose.yml     # Primary deployment definition
└── README.md
```

---

## Local Development

```bash
# Start the full stack (API, PostgreSQL, frontend, Prometheus, Grafana)
docker compose up --build

# Run tests (requires PostgreSQL)
python -m pytest api/ -v

# Import or re-import dataset manually
python scripts/import_bylaws.py --dataset dataset/bylaws_dataset.json --replace-existing
```

Configure environment via `.env` (copy from `.env.example`):

```
POSTGRES_PASSWORD=your-strong-password
API_KEY=your-256-bit-key
```

---

## Disclaimer

This system provides informational legal guidance and retrieval assistance based on Maharashtra Model Bye-laws. It does not replace registered bye-laws, legal counsel, or society-specific official records. Always verify against the society's registered bye-laws and applicable statutory sources. The system is not a substitute for professional legal advice.
