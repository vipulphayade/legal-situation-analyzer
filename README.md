# Legal Situation Analyzer

Hybrid retrieval system for Maharashtra Cooperative Housing Society bye-laws. Analyzes housing society situations, maps them to the most relevant model bye-law, explains the match in plain English, and provides practical guidance.

**API version:** `4.0.0`

---

## Overview

| Capability | Implementation |
|---|---|
| Retrieval | Hybrid: semantic (SentenceTransformers + pgvector) + keyword/topic scoring + cross-encoder reranker |
| Query understanding | Topic detection (13 groups), intent classification (12 patterns), section-reference extraction |
| Strategy selection | `EXACT_CITATION`, `KEYWORD_SEMANTIC`, or `HYBRID_RERANKER` per query |
| Session store | PostgreSQL-backed, 5-minute TTL, shared across replicas |
| Observability | 11 Prometheus metrics, provisioned Grafana dashboard |
| Security | API key auth, rate limiting (slowapi), CORS, trusted host filtering, production env validation |
| Frontend | Dual: legacy static UI (`/`) + React/TypeScript SPA (`/modern/`) behind NGINX |

---

## Architecture

```
Browser ──► NGINX (:8080)
              ├── /api/* ──► FastAPI (:8000)
              │                 POST /analyze     (API key + rate-limited)
              │                 POST /followup    (API key + rate-limited)
              │                 GET  /health
              │                 GET  /metrics     (API key)
              ├── /modern/* ──► React SPA
              └── /* ──► Legacy static UI
```

**Retrieval pipeline:**

```
Query ──► Query Understanding ──► Exact citation? ──► Direct DB lookup ──► Response
                                   │
                                   └─ General query ──► Fetch all candidates
                                                          │
                                                          ├─ Score: semantic + lexical + topic bias + exact bonus
                                                          ├─ Rerank top-20 (cross-encoder)
                                                          ├─ Merge reranked + heuristic order
                                                          ├─ Confidence: score×0.85 + gap×0.15 + consensus_bonus
                                                          └─ Clarification tiers: <0.35 / <0.55 / <0.65 / >=0.65
```

**Query understanding** classifies every query before retrieval:

- **13 topic groups**: `agm`, `parking`, `maintenance`, `transfer`, `redevelopment`, `audit`, `membership`, `complaint`, `committee`, `elections`, `recovery`, `defaulters`, `property`
- **Intent patterns**: permission, prohibition, eligibility, obligation, violation, procedure, deadline, fee, responsibility, rights, dispute, information
- **Section-reference extraction**: `detect_bye_law_reference()` matches `bye-law 126`, `section 94(3)`, `bylaw 12(i)` (including Roman numerals). Exact references bypass scoring.
- **Clarification logic** (4 tiers):

| Range | Behavior |
|-------|----------|
| < 0.35 | Always clarify (NO_MATCH) |
| 0.35–0.55 | Clarify (LOW confidence) |
| 0.55–0.65 | Clarify only if broad or low-signal |
| >= 0.65 | No clarification (MEDIUM/HIGH) |

---

## Repository Structure

```
legal-situation-analyzer/
├── api/                   # 15 app modules + 6 test files (FastAPI)
├── dataset/               # 247-record, 57-field canonical dataset
├── database/              # PostgreSQL + pgvector init schema
├── docker/                # Dockerfiles (api, database, frontend)
├── frontend/              # Legacy static UI
├── frontend-modern/       # React/TypeScript SPA
├── scripts/               # 53 dataset extraction and analysis tools
├── tests/                 # Benchmark suites and eval runners
├── alembic/               # Database migrations
├── prometheus/            # prometheus.yml
├── grafana/               # Provisioned dashboards and datasource
├── kubernetes/            # 4 standalone deployment manifests
├── docs/                  # Architecture notes, audit reports, action plans
├── docker-compose.yml     # Primary deployment definition
└── README.md
```

---

## Dataset

**247 records, 57 fields** — Maharashtra Cooperative Housing Society Model Bye-laws. Source-grounded legal text with explanations, keywords, topic groups, and guidance fields.

Representative fields: `section`, `subsection`, `title`, `chapter`, `topic`, `topic_group`, `keywords`, `technical_terms`, `official_legal_text`, `source_grounded_official_text`, `retrieval_text`, `plain_english`, `why_this_applies`, `real_world_examples`, `common_disputes`, `conditions_required`, `documents_to_check`, `member_rights`, `official_grounding_status`, `primary_retrieval_text`.

### Startup validation

On startup the backend runs five sanity checks against the database:

| Check | Description |
|-------|-------------|
| Section continuity | Detects missing numeric section numbers |
| Subsection gaps | Detects missing subsection letters (a, b, c, ...) |
| Duplicates | Detects duplicate section/subsection pairs |
| Missing text | Detects empty or too-short content fields |
| Missing embeddings | Detects rows without embedding vectors |

Also enforces configurable `MINIMUM_DATASET_SIZE` and verifies embedding completeness and structural integrity before declaring the dataset ready.

---

## Infrastructure

### Docker Compose (primary deployment)

```
docker compose up --build
```

| Service | Image | Port | Depends on |
|---------|-------|------|------------|
| `db` | Custom (PostgreSQL 16 + pgvector) | — | — |
| `api` | Custom (Python 3.12 + FastAPI) | `:8000` | `db` healthy |
| `frontend` | Custom (NGINX 1.27) | `:8080` | `api` healthy |
| `prometheus` | `prom/prometheus:v2.55.1` | `:9090` | `api` healthy |
| `grafana` | `grafana/grafana-oss:11.3.0` | `:3000` | `prometheus` started |

### URLs

| Address | What |
|---------|------|
| `http://localhost:8080/` | Legacy frontend |
| `http://localhost:8080/modern/` | Modern frontend |
| `http://localhost:8000/health` | Health check |
| `http://localhost:8000/metrics` | Prometheus metrics |
| `http://localhost:9090/` | Prometheus UI |
| `http://localhost:3000/` | Grafana (admin / admin) |

### Kubernetes

Four standalone manifests in `kubernetes/`:
- `api-deployment.yaml` — FastAPI deployment with health probes
- `frontend-deployment.yaml` — NGINX deployment serving both UIs
- `postgres-deployment.yaml` — PostgreSQL + pgvector StatefulSet
- `app-secret.yaml` — Secret template for DB credentials and API key

Not currently connected to CI/CD. Ready for manual `kubectl apply -f kubernetes/`.

### Local development

```bash
docker compose up --build

# Manual dataset import (outside Docker)
python scripts/import_bylaws.py
python scripts/import_bylaws.py --dataset dataset/bylaws_dataset.json --replace-existing

# Run tests
python -m pytest api/ -v
```

---

## Observability

### Prometheus metrics (11 metric families)

| Metric | Type | Purpose |
|--------|------|---------|
| `legal_analyzer_api_requests_total` | Counter | Request count by method, path, status |
| `legal_analyzer_api_request_duration_seconds` | Histogram | API latency distribution |
| `legal_analyzer_retrieval_duration_seconds` | Histogram | Retrieval pipeline latency |
| `legal_analyzer_reranker_duration_seconds` | Histogram | Cross-encoder latency |
| `legal_analyzer_db_pool` | Gauge | Pool size / checked-in / overflow (reported every 15s) |
| `legal_analyzer_negative_score_total` | Counter | Candidates with non-positive scores |
| `legal_analyzer_retrieval_failures_total` | Counter | Failed or no-match retrievals |
| `legal_analyzer_candidate_count` | Histogram | Candidate pool size distribution |
| `legal_analyzer_top_score` | Histogram | Best heuristic score before reranking |
| `legal_analyzer_final_confidence` | Histogram | Final confidence returned to client |
| `legal_analyzer_clarification_total` | Counter | Clarification needed vs not |

Latency buckets: `[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, 15.0, 30.0]`

### Grafana

Provisioned dashboard at `grafana/dashboards/legal-analyzer.json` with auto-configured Prometheus datasource. Tracks retrieval latency, reranker performance, pool health, confidence distribution, and error rates.

---

## Benchmark

Verified against `tests/retrieval_benchmark.json` (99 queries, Docker + PostgreSQL + reranker):

| Metric | Value |
|--------|-------|
| Top-1 accuracy | 75.8% |
| Top-3 accuracy | 81.8% |
| Top-5 accuracy | 92.9% |
| MRR | 0.8095 |
| Errors | 0 |

**Run:** `python api/_run_benchmark.py` (requires PostgreSQL)

The benchmark serves as the project's regression gate. Any retrieval change must maintain or improve these numbers against the same 99-query suite before being considered safe to merge.

---

## Security & Production Hardening

| Feature | Detail | Engineering notes |
|---------|--------|------------------|
| API key auth | `X-API-Key` via `auth.py` | `secrets.compare_digest()` for timing-safe comparison. Disabled if `API_KEY` unset. |
| Rate limiting | `slowapi`, default 20/min | Respects `X-Forwarded-For` for proxy environments |
| CORS | Configurable origins | Default restricts to `localhost:8080` |
| Trusted hosts | Configurable allowlist | Default `localhost,127.0.0.1,api,frontend` |
| Security headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Cache-Control` | Applied via middleware on every response |
| Production env validation | `PRODUCTION=1` | Fails startup on missing/placeholder `API_KEY` or `DB_PASSWORD` |
| Graceful shutdown | 25-second drain | Waits for active requests, then closes DB connections |
| DB connection pool | Size 10, overflow 10, timeout 30s, recycle 3600s | Pool metrics reported every 15s via daemon thread |
| Request timeout | Default 30s, configurable | Returns 504 on timeout |

---

## Testing

74 collected tests across 6 files:

| File | Tests | Focus |
|------|-------|-------|
| `test_import.py` | 14 | Dataset import, field extraction, fallback behavior |
| `test_fixes.py` | 43 | Regex, confidence labels, clarification tiers, reranker integration |
| `test_auth.py` | 1 | API key rejection |
| `test_health.py` | 1 | Health endpoint DB connectivity |
| `test_embeddings.py` | 2 | Embedding model loading |
| `test_session.py` | 1 | Session context key verification |

60 pass, 6 require PostgreSQL, 8 skipped without `--reranker`.

---

## Version History

| Range | Focus |
|-------|-------|
| v1–v9 | Foundational legal retrieval prototypes, editorial workspace identity |
| v10–v14 | Frontend modernization (React, Tailwind), UX iterations |
| v15–v17 | Hybrid retrieval, cross-encoder reranking, query understanding, Prometheus + Grafana observability |
| v18–v20 | Production hardening, benchmarking discipline, deployment maturity, retrieval quality improvements |

---

## Known Limitations

- Cross-encoder adds ~200–220ms CPU latency per query (`cross-encoder/ms-marco-MiniLM-L-6-v2`)
- 6 integration tests require a running PostgreSQL database
- Dataset covers Maharashtra Model Bye-laws only (not registered bye-laws of individual societies)
- Kubernetes manifests are standalone (not wired to CI/CD)
- Follow-up context expires after 5 minutes

---

## Future Work

- **Expanded query-understanding coverage:** Add topic groups for financial governance, dispute resolution, member rights
- **Stratified benchmark suite:** Organize the 99-query benchmark by topic group for per-topic regression detection
- **Automated CI benchmark gate:** Run benchmark on every retrieval PR; fail if Top-1 or MRR drops below locked baseline
- **Dataset augmentation pipeline:** Formalize scraped-HTML → extracted verbatim → dataset merge into a repeatable, versioned workflow with diff review
- **Reranker model evaluation:** Benchmark alternative cross-encoder models against the 99-query suite
- **Production readiness automation:** Convert `PRODUCTION_READINESS_AUDIT.md` into a runnable startup assertion

---

## Disclaimer

This system provides informational legal guidance and retrieval assistance. It does not replace registered bye-laws, legal counsel, or society-specific official records. Always verify against the society's registered bye-laws and applicable statutory sources.
