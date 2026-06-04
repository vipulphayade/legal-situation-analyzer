# Production Readiness Audit — Legal Situation Analyzer

**Audit Date:** 2026-06-01  
**Auditor:** Principal Software Engineer / Security / DevOps Review  
**Repository:** `legal-situation-analyzer`  
**Status:** NOT READY for production

---

## Executive Summary

This audit examined all 18 Python files, 3 Dockerfiles, docker-compose.yml, 4 Kubernetes manifests, 3 frontend implementations, database schema, Alembic migrations, 3 dataset copies, and all configuration files in the repository.

**The project is NOT READY for production.** It has critical hallucination risks from fallback content generation, hardcoded placeholder credentials, missing restart policies, a broken Alembic path for local development, and an authentication system that silently self-disables.

The application can run in Docker under ideal conditions, but it has insufficient guardrails for unsupervised production operation.

---

## Production Readiness Verdict

**STAGING READY with caveats** — The Docker compose stack starts and serves health/metrics endpoints. The following conditions must be met before considering production deployment:

- `POSTGRES_PASSWORD` and `API_KEY` must be changed from placeholders
- `restart: unless-stopped` must be added to every service
- The duplicate dataset copy must be reconciled
- The fallback dataset path (silent AI template content) must be guarded
- The `MINIMUM_DATASET_SIZE` default must match the actual dataset

---

## Critical (P0) Findings

### P0.1 — Silent fallback to AI-template-generated legal content

| Field | Value |
|---|---|
| **Files** | `api/import_service.py:310`, `api/bylaw_seed.py:751-787` |
| **Evidence** | `load_dataset()` at line 310: `return build_dataset()` when JSON file is missing/unreadable. `build_dataset()` produces 277 entries with `default_content()` that generates: `"{bylaw_label} deals with {clause_title} and expects the society to follow the registered bye-laws, the Act, and the proper society process on this subject."` |
| **Impact** | If the JSON dataset path is wrong, the file is corrupted, or the file is missing, the system silently serves AI-template-generated placeholder text as legal analysis. No log warning is emitted. |
| **Fix** | Add a log warning at `import_service.py:310`. Add a startup check that fails if the JSON dataset is unavailable rather than silently falling back. |

### P0.2 — Three copies of dataset with version skew

| Field | Value |
|---|---|
| **Files** | `dataset/bylaws_dataset.json` (3,076,969 bytes), `api/bylaws_dataset.json` (3,438,184 bytes), `database/bylaws_dataset.json` (3,076,969 bytes) |
| **Evidence** | The `api/` copy is 361 KB larger than the other two. Code resolves to `dataset/` by default but can load the wrong copy depending on `APP_ROOT`. |
| **Impact** | Inconsistent dataset depending on deployment. Some copies may contain different or outdated legal text. |
| **Fix** | Remove `api/bylaws_dataset.json` and `database/bylaws_dataset.json`. Keep only `dataset/bylaws_dataset.json`. Pin `DEFAULT_DATASET_PATH` to an absolute path or verify the dataset matches an expected checksum at startup. |

### P0.3 — `MINIMUM_DATASET_SIZE` default (1000) exceeds actual dataset (229 entries)

| Field | Value |
|---|---|
| **Files** | `api/import_service.py:521`, `.env.example` |
| **Evidence** | `minimum_expected = int(os.getenv("MINIMUM_DATASET_SIZE", "1000"))` — default is 1000. The dataset has 229 entries. The `.env.example` correctly sets `MINIMUM_DATASET_SIZE=229` but the hardcoded default in code is wrong. |
| **Impact** | On any deployment without the `.env` file, `ensure_seed_data()` fails the integrity check. With `REBUILD_DATASET_ON_STARTUP=0` (default), it logs a warning and continues with empty data. Queries return no results. |
| **Fix** | Change the default in `import_service.py:521` from `"1000"` to `"229"` or validate against actual dataset row count dynamically. |

### P0.4 — Roman numeral subsection matching broken

| Field | Value |
|---|---|
| **Files** | `api/search.py:87` |
| **Evidence** | `pattern = r"\b(?:bye[-\s]?law\|byelaw\|section)\s*(\d{1,3})\s*(?:\(?\s*([a-z])\s*\)?)?\b"` — the `[a-z]` character class only matches lowercase letters. Many Maharashtra bye-laws use uppercase Roman numerals: `12(I)`, `12(II)`, `13(A)`, `13(B)`. |
| **Impact** | A query like "bye-law 12(I)" will match section 12 but NOT recognize subsection `(I)`. The exact-citation path is bypassed, and the query falls through to semantic search, which may return a different bylaw entirely. |
| **Fix** | Change `[a-z]` to `[a-zA-Z]` in both regex patterns on line 87 and 90. |

### P0.5 — `POSTGRES_PASSWORD` and `API_KEY` are placeholder values

| Field | Value |
|---|---|
| **Files** | `.env`, `kubernetes/app-secret.yaml` |
| **Evidence** | `.env`: `POSTGRES_PASSWORD=change-this-before-production`, `API_KEY=` (empty). `app-secret.yaml`: `DB_PASSWORD: replace-this-strong-password`, `API_KEY: change-this-before-production`. |
| **Impact** | Database uses a well-known password. API authentication is disabled (empty API_KEY = no auth). In the current running deployment at `localhost:8000`, every endpoint is unauthenticated and accessible. |
| **Fix** | Generate strong random passwords. Set `API_KEY` to a 256-bit random value. Add `kubernetes/app-secret.yaml` to `.gitignore`. Do not commit plaintext secrets. |

---

## High Severity (P1) Findings

### P1.1 — Auth bypass when API_KEY not set (no startup warning)

| Field | Value |
|---|---|
| **Files** | `api/auth.py:10-12` |
| **Evidence** | `if not api_key: return` — silently disables all authentication. No warning log at startup, no metric, no health check failure. |
| **Impact** | If `API_KEY` env var is accidentally omitted in production, the entire API is publicly accessible with no indication to operators. |
| **Fix** | Add a startup check that logs a CRITICAL warning if `API_KEY` is empty. Consider making auth mandatory in production via environment variable. |

### P1.2 — Docker compose has no restart policies

| Field | Value |
|---|---|
| **Files** | `docker-compose.yml` |
| **Evidence** | No service defines `restart:`. All 5 services (db, api, frontend, prometheus, grafana) will NOT restart if they crash or exit. |
| **Impact** | Any transient failure (OOM, DB connection loss, temporary network issue) causes permanent downtime. |
| **Fix** | Add `restart: unless-stopped` to `db`, `api`, and `frontend` services. |

### P1.3 — `.dockerignore` does not exclude `.env`

| Field | Value |
|---|---|
| **Files** | `.dockerignore` |
| **Evidence** | Current exclusions: `__pycache__`, `*.pyc`, `.git`, `node_modules`, `venv`, `.cache`, `*.log`. No `.env` exclusion. |
| **Impact** | The `.env` file (containing `POSTGRES_PASSWORD` and `API_KEY`) is copied into the Docker build context and could be embedded in image layers. `docker history` can extract it. |
| **Fix** | Add `.env` to `.dockerignore`. |

### P1.4 — Run-migrations script_location path broken for local development

| Field | Value |
|---|---|
| **Files** | `api/database.py:59-63` |
| **Evidence** | `str(Path(__file__).resolve().parent / "alembic")` resolves to `.../api/alembic/` which does not exist locally. The real `alembic/` directory is at the project root. Works in Docker only because `COPY alembic/ /app/alembic/` places it at `/app/alembic/`. |
| **Impact** | Developers cannot run the API locally outside Docker. Running `uvicorn main:app` from the project root crashes on startup. |
| **Fix** | Use an env var for script location, or try multiple candidate paths, or symlink. |

### P1.5 — `import_dataset()` data-loss window from broken transaction atomicity

| Field | Value |
|---|---|
| **Files** | `api/import_service.py:322-324, 480, 501-503` |
| **Evidence** | `TRUNCATE ... RESTART IDENTITY CASCADE` + `db.commit()` is executed BEFORE the INSERTs. Another `db.commit()` happens after INSERTs. If the process crashes between commit 1 and commit 2, data is permanently lost. |
| **Impact** | During `REBUILD_DATASET_ON_STARTUP=1` or manual re-import, a crash leaves the database empty. |
| **Fix** | Remove the intermediate commit. Wrap truncate + insert in a single transaction. |

### P1.6 — Grafana defaults to admin/admin credentials

| Field | Value |
|---|---|
| **Files** | `docker-compose.yml:88-89` |
| **Evidence** | `GF_SECURITY_ADMIN_USER: ${GF_SECURITY_ADMIN_USER:-admin}`, `GF_SECURITY_ADMIN_PASSWORD: ${GF_SECURITY_ADMIN_PASSWORD:-admin}`. Neither is set in `.env`. |
| **Impact** | Anyone with network access to Grafana (port 3000) can log in with `admin`/`admin` and access all dashboards and metrics. |
| **Fix** | Set strong Grafana credentials in `.env`. |

### P1.7 — `answer_followup()` silently swallows errors and uses deprecated `context` path

| Field | Value |
|---|---|
| **Files** | `api/search.py:793-796`, `api/main.py:144-151` |
| **Evidence** | `try: confidence = float(...) except Exception: confidence = 0.0` — overly broad exception. The `FollowupRequest` schema still accepts `context` (the full response object sent by the classic frontend), with no validation. A client can inject arbitrary context data. |
| **Impact** | A malicious client can craft a fake session context and receive follow-up answers based on fabricated data. The deprecated path has no authentication of context provenance. |
| **Fix** | Remove the `context` field from `FollowupRequest`. Require `session_token` exclusively. Remove or tighten exception handling. |

### P1.8 — No connection timeout or SSL for PostgreSQL

| Field | Value |
|---|---|
| **Files** | `api/database.py:32-39` |
| **Evidence** | `create_engine(DATABASE_URL, ...)` with no `connect_args`. No `connect_timeout`, no `sslmode`. |
| **Impact** | If the database is unreachable, the application hangs for the OS TCP timeout (typically 21-127 seconds). Traffic to the database is unencrypted. |
| **Fix** | Add `connect_args={"connect_timeout": 10}` and `sslmode=require` via env var. |

---

## Medium Severity (P2) Findings

### P2.1 — Brute-force full table scan instead of using HNSW index

`api/search.py:373-416` — `fetch_all_candidates()` does `SELECT * FROM bylaws` and computes cosine similarity in Python for all rows. The database has a properly configured HNSW index (`bylaws_embedding_idx`) that is never used. For 229 rows this is acceptable, but it does not scale and wastes the index.  
**File:** `api/search.py`

### P2.2 — Hash-bucket fallback embedding is not semantic and has no logging

`api/embeddings.py:29-30` — `except Exception: self._fallback = True`. If the SentenceTransformer model fails to load (e.g., transient network issue downloading from HuggingFace Hub), the system silently degrades to a hash-bucket embedding that has no semantic meaning. No log, no metric.  
**File:** `api/embeddings.py`

### P2.3 — Three separate topic/keyword definitions across the codebase

`search.py:29-43`, `query_understanding.py:7-15`, `bylaw_seed.py:280-293` — Three different keyword sets define topics. Adding a topic to one but not the others causes `detect_topic()`, `expand_keywords()`, and dataset building to diverge.  
**Files:** `api/search.py`, `api/query_understanding.py`, `api/bylaw_seed.py`

### P2.4 — `session_context` references `"content"` which is never in the response

`api/main.py:120-125` — `session_context` includes `"content"` but the `AnalyzeResponse` schema does not have a `content` field. The field is always missing from `result.get("content")`, so it is never stored in the session. Follow-up answers that need content fall through to generic responses.  
**File:** `api/main.py`

### P2.5 — `session_store.token` is TEXT with no length limit

`alembic/versions/002_add_session_store.py:25` — `token` is `sa.Text()`. Should be `sa.String(64)` to guard against abnormally long tokens.  
**File:** `alembic/versions/002_add_session_store.py`

### P2.6 — No index on `session_store.created_at` for TTL cleanup

`api/session_store.py:44`, migration 002 — `DELETE FROM session_store WHERE created_at < NOW() - INTERVAL '300 seconds'` runs without an index on `created_at`. Full table scan on every cleanup.  
**Files:** `api/session_store.py`, `alembic/versions/002_add_session_store.py`

### P2.7 — `bylaw_relations` lacks foreign key constraints and allows duplicates

`alembic/versions/001_initial_schema.py:101-111` — No `FOREIGN KEY` to `bylaws(section, subsection)`. No `UNIQUE` constraint on `(source, target)`. Data integrity is not enforced at the database level.  
**File:** `alembic/versions/001_initial_schema.py`

### P2.8 — `schema_version` table is orphaned

`alembic/versions/001_initial_schema.py:21-25, 124` — Table is created and populated with version=2, but no code ever reads it. The INSERT is non-idempotent. No primary key. Dead artifact.  
**File:** `alembic/versions/001_initial_schema.py`

### P2.9 — Tests and build artifacts included in production Docker image

`docker/Dockerfile.api` — `COPY api/ /app/` copies test files (`test_*.py`), `__pycache__`, `.pytest_cache`, and the duplicate `api/bylaws_dataset.json` into the production image.  
**File:** `docker/Dockerfile.api`

### P2.10 — HuggingFace models downloaded at every container restart

`docker/Dockerfile.api:6` — `HF_HOME=/tmp/huggingface` stores downloaded models in ephemeral `/tmp`. Every container restart re-downloads the SentenceTransformer model (~90MB).  
**File:** `docker/Dockerfile.api`

### P2.11 — Modern frontend silently swallows follow-up errors

`frontend-modern/src/App.tsx:243-244` — `catch { setFollowupStatus("error") }` shows no error message to the user when a follow-up request fails. The error is silently swallowed.  
**File:** `frontend-modern/src/App.tsx`

### P2.12 — No index on `bylaw_relations(target_section, target_subsection)` for JOIN performance

`search.py:484-501` queries `JOIN bylaws ON b.section=r.target_section AND b.subsection=r.target_subsection`. No index covers the right side of this JOIN.  
**Files:** `alembic/versions/001_initial_schema.py`, `api/search.py`

### P2.13 — `bylaws` table is very wide (33 columns) but all columns are fetched on every query

`search.py:373-416` uses `SELECT *`, pulling all TEXT arrays and embedding vectors even though only a subset of columns is needed for scoring.  
**Files:** `api/search.py`, `alembic/versions/001_initial_schema.py`

### P2.14 — No CSRF protection on API

`main.py:71-79` — `CORSMiddleware` does not set `allow_origins` dynamically from request origin. No CSRF cookie-based tokens.  
**File:** `api/main.py`

---

## Low Severity (P3) Findings

- **P3.1:** `prompt_builder.py` is dead code (20 lines, never imported or called)
- **P3.2:** `v9_reference_frontend/` is dead code (5 files, never referenced by any Dockerfile or compose)
- **P3.3:** pgvector extension created in two places (`init.sql:1` and `001_initial_schema.py:26`)
- **P3.4:** Session TTL is hardcoded at 300 seconds (`session_store.py:32,45`)
- **P3.5:** `alembic.ini` logging configuration is never loaded at runtime
- **P3.6:** `query_logs` has no timestamp index for future analytics queries
- **P3.7:** No `start_period` on `db` health check (PostgreSQL initialization can exceed 50s on first run)
- **P3.8:** Frontend has no health check in docker-compose
- **P3.9:** Kubernetes frontend deployment has no readiness/liveness probes
- **P3.10:** Classic frontend has no fetch timeout or AbortController (modern frontend also lacks it)
- **P3.11:** Kubernetes API deployment memory limit (256Mi) may be tight for HuggingFace model loading
- **P3.12:** No API versioning prefix (`/v1/analyze`)
- **P3.13:** Duplicate `.sr-only` CSS class defined twice in `frontend/styles.css`
- **P3.14:** `parse_embedding()` silently returns `[]` on any exception
- **P3.15:** `EmbeddingService.load()` never retries model download after first failure
- **P3.16:** Rate limiter uses `get_remote_address` which sees proxy IP behind nginx/k8s

---

## Release Blockers

These must be fixed before any production deployment:

1. **REQUIRED:** Change `POSTGRES_PASSWORD` and `API_KEY` from placeholders to strong random values in `.env` and `kubernetes/app-secret.yaml`
2. **REQUIRED:** Add `restart: unless-stopped` to `db`, `api`, `frontend` services in `docker-compose.yml`
3. **REQUIRED:** Reconcile 3 dataset copies — delete `api/bylaws_dataset.json` and `database/bylaws_dataset.json`, keep only `dataset/bylaws_dataset.json`
4. **REQUIRED:** Fix `MINIMUM_DATASET_SIZE` default from 1000 to match actual dataset size (229)
5. **REQUIRED:** Fix Roman numeral regex in `search.py:87` to match uppercase subsections
6. **REQUIRED:** Add `warning`-level log when `load_dataset()` falls back to `build_dataset()`
7. **REQUIRED:** Remove the intermediate `db.commit()` in `import_dataset()` that causes a data-loss window
8. **REQUIRED:** Add `.env` to `.dockerignore` to prevent secret leakage into Docker images

---

## Recommended Fix Order

### Week 1 — Security (must go first)

1. P0.5 — Change passwords and API keys
2. P1.3 — Fix `.dockerignore`
3. P1.2 — Add restart policies
4. P1.1 — Add auth-bypass startup warning
5. P1.6 — Fix Grafana credentials

### Week 2 — Startup reliability

6. P0.3 — Fix MINIMUM_DATASET_SIZE
7. P1.4 — Fix Alembic script_location for local dev
8. P0.2 — Reconcile dataset copies
9. P0.1 — Add fallback dataset warning

### Week 3 — Data integrity

10. P1.5 — Fix import transaction atomicity
11. P2.7 — Add foreign keys and unique constraints
12. P2.5 — Fix session_store token length
13. P2.8 — Remove orphaned schema_version table

### Week 4 — Retrieval quality

14. P0.4 — Fix Roman numeral regex
15. P2.1 — Use HNSW index instead of brute-force scan
16. P2.3 — Consolidate topic keywords

### Week 5 — Observability and hardening

17. P1.7 — Remove deprecated `context` follow-up path
18. P2.2 — Add logging/metrics for embedding fallback
19. P2.6 — Add session_store created_at index
20. P1.8 — Add DB connection timeout and SSL

---

## What Works Well

- Clean multi-stage Docker builds with non-root users
- Proper Kubernetes security contexts (seccomp, cap-drop, runAsNonRoot)
- Good HNSW index configuration (even though it's not used at runtime)
- Sensible middleware stack (CORS, TrustedHost, security headers)
- Proper Pydantic validation on request inputs
- Parameterized SQL queries (no SQLi vector)
- Horizontal health check dependencies in docker-compose (`condition: service_healthy`)
- Proper use of `pool_pre_ping` in SQLAlchemy connection pool
- `secrets.compare_digest` for API key comparison (constant-time)
- Good separation of concerns between classic and modern frontends
- Prometheus metrics instrumentation
- Rate limiting via slowapi

---

## Final Assessment

This project is development-complete but not production-hardened. The core retrieval pipeline is functionally correct under ideal conditions (dataset present, model downloads succeed, environment variables set), but it has insufficient defense-in-depth.

The project is approximately **2-3 weeks of focused engineering work** away from a defensible production launch, assuming one engineer working full-time on production hardening.

---

## Improvement Opportunities

These are NOT bugs. These are optional improvements that could materially improve accuracy, reliability, maintainability, scalability, observability, security, developer experience, deployment experience, cost efficiency, or future feature development.

---

### AI and Retrieval

#### I1. Use HNSW index for ANN search instead of brute-force (HIGH IMPACT, MEDIUM INVESTMENT)

| Field | Value |
|---|---|
| **Category** | Performance |
| **Current** | `fetch_all_candidates()` does `SELECT *` on all rows, computes cosine similarity in Python |
| **Proposed** | Use `SELECT *, embedding <-> :query_embedding AS distance FROM bylaws ORDER BY distance LIMIT 50` |
| **Benefit** | ~50x speedup on large datasets. Reduces memory pressure. Actualizes the value of the existing HNSW index |
| **Risk** | May change ranking order slightly (ANN vs exact). Compare results before switching |
| **Effort** | 2-3 days |
| **Priority** | **DO BEFORE PRODUCTION LAUNCH** |

#### I2. Implement re-ranker stage (MEDIUM IMPACT, MAJOR REFACTOR)

| Field | Value |
|---|---|
| **Category** | Retrieval quality |
| **Current** | Single-pass scoring with hardcoded weights |
| **Proposed** | Implement a lightweight cross-encoder re-ranker (e.g., `cross-encoder/ms-marco-MiniLM-L-6-v2`) to re-score top-20 candidates |
| **Benefit** | Significant improvement in ranking quality. Cross-encoders are more accurate than bi-encoders |
| **Risk** | Adds latency (~50ms per candidate pair). Added dependency |
| **Effort** | 1-2 weeks |
| **Priority** | WAIT UNTIL AFTER PRODUCTION LAUNCH |

#### I3. Consolidate keyword/topic definitions into a single config file (MEDIUM IMPACT, QUICK WIN)

| Field | Value |
|---|---|
| **Category** | Maintainability |
| **Current** | 3 separate keyword definitions in `search.py`, `query_understanding.py`, `bylaw_seed.py` |
| **Proposed** | Create a single `api/topic_config.py` that exports `TOPIC_KEYWORDS`, `SYNONYM_GROUPS`, `TOPIC_RULES` |
| **Benefit** | Single source of truth. Adding a new topic updates all systems atomically |
| **Risk** | Low — refactoring only |
| **Effort** | 1 day |
| **Priority** | **DO BEFORE PRODUCTION LAUNCH** |

#### I4. Use `primary_retrieval_text` from dataset (MEDIUM IMPACT, QUICK WIN)

| Field | Value |
|---|---|
| **Category** | Retrieval quality |
| **Current** | Dataset has `primary_retrieval_text` field (designed for "official-text-first" retrieval) but code never reads it |
| **Proposed** | Include `primary_retrieval_text` in `fetch_all_candidates()` selection and use it as the preferred embedding source |
| **Benefit** | Better alignment with dataset's intended retrieval strategy |
| **Risk** | Low |
| **Effort** | 0.5 day |
| **Priority** | **DO BEFORE PRODUCTION LAUNCH** |

---

### Backend

#### I5. Add API versioning prefix (LOW IMPACT, QUICK WIN)

| Field | Value |
|---|---|
| **Category** | API design |
| **Current** | Endpoints at `/analyze`, `/followup` |
| **Proposed** | Move to `/v1/analyze`, `/v1/followup`. Keep old paths with deprecation redirect |
| **Benefit** | Allows future breaking changes without breaking existing clients |
| **Risk** | Low, but requires frontend updates |
| **Effort** | 0.5 day |
| **Priority** | WAIT UNTIL AFTER PRODUCTION LAUNCH |

#### I6. Make session TTL configurable via env var (LOW IMPACT, QUICK WIN)

| Field | Value |
|---|---|
| **Category** | Configuration |
| **Current** | Hardcoded 300 seconds in `session_store.py:32,45` |
| **Proposed** | `os.getenv("SESSION_TTL_SECONDS", "300")` |
| **Benefit** | Operational flexibility |
| **Risk** | Low |
| **Effort** | 0.5 hour |
| **Priority** | **DO BEFORE PRODUCTION LAUNCH** |

#### I7. Add `pool_recycle` to SQLAlchemy engine (LOW IMPACT, QUICK WIN)

| Field | Value |
|---|---|
| **Category** | Database |
| **Current** | No connection recycling. Long-lived connections may be dropped by PgBouncer, AWS RDS proxy, or the database itself |
| **Proposed** | Add `pool_recycle=3600` to `create_engine()` call |
| **Benefit** | Prevents connection stall errors on long-running deployments |
| **Risk** | Low |
| **Effort** | 0.5 hour |
| **Priority** | **DO BEFORE PRODUCTION LAUNCH** |

#### I8. Add request body size limit (LOW IMPACT, QUICK WIN)

| Field | Value |
|---|---|
| **Category** | Security |
| **Current** | No global limit. Only Pydantic field limits (3000 chars on description) |
| **Proposed** | `app.add_middleware(RequestBodySizeMiddleware, max_size=4096)` or similar |
| **Benefit** | Prevents resource exhaustion from oversized requests |
| **Risk** | Low |
| **Effort** | 0.5 hour |
| **Priority** | **DO BEFORE PRODUCTION LAUNCH** |

---

### Database

#### I9. Add soft-delete to `session_store` or use background vacuum (LOW IMPACT, QUICK WIN)

| Field | Value |
|---|---|
| **Category** | Database |
| **Current** | Expired sessions are deleted lazily on `get()` and at startup |
| **Proposed** | Add an index on `created_at` and optionally schedule periodic vacuum on the table |
| **Benefit** | Prevents table bloat from accumulated dead tuples |
| **Risk** | Low |
| **Effort** | 1 day |
| **Priority** | WAIT UNTIL AFTER PRODUCTION LAUNCH |

#### I10. Add CHECK constraints for data quality (LOW IMPACT, MEDIUM INVESTMENT)

| Field | Value |
|---|---|
| **Category** | Data integrity |
| **Current** | No database-level CHECK constraints |
| **Proposed** | Add `CHECK (confidence BETWEEN 0 AND 1)` for query_logs, `CHECK (section ~ '^[0-9]+$')` for bylaws |
| **Benefit** | Database enforces data quality even if application logic has bugs |
| **Risk** | Migrations may fail if existing data violates constraints |
| **Effort** | 1-2 days |
| **Priority** | WAIT UNTIL AFTER PRODUCTION LAUNCH |

---

### Frontend

#### I11. Add fetch timeout/AbortController to both frontends (MEDIUM IMPACT, QUICK WIN)

| Field | Value |
|---|---|
| **Category** | UX |
| **Current** | No timeout on fetch calls. Requests can hang indefinitely |
| **Proposed** | Wrap fetch in `AbortController` with 30-second timeout. Show user-friendly timeout message |
| **Benefit** | Better UX. No hung requests consuming resources |
| **Risk** | Low |
| **Effort** | 1 day |
| **Priority** | **DO BEFORE PRODUCTION LAUNCH** |

#### I12. Add `aria-live` regions to modern frontend (LOW IMPACT, QUICK WIN)

| Field | Value |
|---|---|
| **Category** | Accessibility |
| **Current** | Modern frontend lacks `aria-live` regions that the classic frontend has |
| **Proposed** | Add `aria-live="polite"` to status/result containers |
| **Benefit** | Screen reader accessibility |
| **Risk** | Low |
| **Effort** | 0.5 day |
| **Priority** | NICE TO HAVE |

#### I13. Remove classic frontend and make modern frontend the default (MEDIUM IMPACT, MEDIUM INVESTMENT)

| Field | Value |
|---|---|
| **Category** | Maintainability |
| **Current** | Two frontends served side-by-side. Classic at `/`, modern at `/modern/` |
| **Proposed** | Move modern frontend to `/`, remove classic frontend code |
| **Benefit** | Eliminates maintenance burden of two frontends. Removes dead code |
| **Risk** | All users must have JS enabled (modern frontend is a React SPA). Classic frontend works without JS |
| **Effort** | 3-5 days |
| **Priority** | WAIT UNTIL AFTER PRODUCTION LAUNCH — maintain dual-frontend during migration period |

---

### Operations

#### I14. Add structured logging (MEDIUM IMPACT, MEDIUM INVESTMENT)

| Field | Value |
|---|---|
| **Category** | Observability |
| **Current** | Python `logging` module with basic string formatting |
| **Proposed** | Use `structlog` or JSON logging. Include correlation IDs, request IDs, timing |
| **Benefit** | Machine-parseable logs. Better debugging in production |
| **Risk** | Low, but requires log infrastructure changes |
| **Effort** | 3-5 days |
| **Priority** | **DO BEFORE PRODUCTION LAUNCH** |

#### I15. Add health endpoint to return DB connection status (MEDIUM IMPACT, QUICK WIN)

| Field | Value |
|---|---|
| **Category** | Observability |
| **Current** | `/health` returns `{"status":"ok"}` without checking DB connectivity |
| **Proposed** | Include `"database": "ok"` or `"database": "error"` based on a simple `SELECT 1` |
| **Benefit** | Health check actually verifies the application can serve requests, not just that the port is open |
| **Risk** | Low |
| **Effort** | 0.5 day |
| **Priority** | **DO BEFORE PRODUCTION LAUNCH** |

#### I16. Pre-download HuggingFace model during Docker build (MEDIUM IMPACT, MEDIUM INVESTMENT)

| Field | Value |
|---|---|
| **Category** | Deployment |
| **Current** | Model downloaded at runtime on first request. Fails on startup if network is unavailable |
| **Proposed** | Add a multi-stage build step that pre-downloads the model to a directory, then copy it into the final image |
| **Benefit** | No model download at runtime. Faster container startup. Works in air-gapped environments |
| **Risk** | Increases image size by ~90MB. Requires build-time network access |
| **Effort** | 1-2 days |
| **Priority** | **DO BEFORE PRODUCTION LAUNCH** |

#### I17. Add startup validation for required env vars (MEDIUM IMPACT, QUICK WIN)

| Field | Value |
|---|---|
| **Category** | Operations |
| **Current** | Missing required env vars cause failures at first request, not at startup |
| **Proposed** | Add a startup function that validates `DB_PASSWORD`, `API_KEY`, `DATABASE_URL` format. Exit with clear error message if any are missing |
| **Benefit** | Fail fast. Clear operator feedback |
| **Risk** | Low |
| **Effort** | 0.5 day |
| **Priority** | **DO BEFORE PRODUCTION LAUNCH** |

---

### Scalability

#### I18. Make `get_remote_address` respect X-Forwarded-For for rate limiting (MEDIUM IMPACT, QUICK WIN)

| Field | Value |
|---|---|
| **Category** | Security |
| **Current** | slowapi's `get_remote_address` uses `request.client.host`, which is the proxy IP behind nginx/k8s |
| **Proposed** | Configure slowapi to use `request.headers.get("X-Forwarded-For", "").split(",")[0].strip()` when behind a trusted proxy |
| **Benefit** | Correct per-client rate limiting behind reverse proxies |
| **Risk** | Low if only trusted proxies forward headers |
| **Effort** | 0.5 day |
| **Priority** | **DO BEFORE PRODUCTION LAUNCH** |

#### I19. Add Horizontal Pod Autoscaler for API and frontend (LOW IMPACT, MEDIUM INVESTMENT)

| Field | Value |
|---|---|
| **Category** | Scalability |
| **Current** | Kubernetes deployments have fixed replica counts |
| **Proposed** | Add HPA targeting 70% CPU utilization for API and frontend |
| **Benefit** | Auto-scales with traffic |
| **Risk** | API HPA may cause migration race conditions if multiple pods start simultaneously |
| **Effort** | 1-2 days |
| **Priority** | WAIT UNTIL AFTER PRODUCTION LAUNCH |

#### I20. Add PodDisruptionBudget for zero-downtime deployments (LOW IMPACT, QUICK WIN)

| Field | Value |
|---|---|
| **Category** | Scalability |
| **Current** | No PDB. All pods can be disrupted simultaneously during node maintenance |
| **Proposed** | `minAvailable: 1` for API and frontend |
| **Benefit** | Ensures at least one replica remains available during rolling updates |
| **Effort** | 0.5 day |
| **Priority** | WAIT UNTIL AFTER PRODUCTION LAUNCH |

---

### Testing

#### I21. Add startup integration test (MEDIUM IMPACT, QUICK WIN)

| Field | Value |
|---|---|
| **Category** | Testing |
| **Current** | No test verifies the application starts successfully |
| **Proposed** | Add a test that starts uvicorn in a subprocess, hits `/health`, and verifies 200 response |
| **Benefit** | Catches import errors, missing dependencies, startup crashes before deployment |
| **Risk** | Low |
| **Effort** | 0.5 day |
| **Priority** | **DO BEFORE PRODUCTION LAUNCH** |

#### I22. Add database round-trip integration test (MEDIUM IMPACT, QUICK WIN)

| Field | Value |
|---|---|
| **Category** | Testing |
| **Current** | Tests use mock DB or no DB |
| **Proposed** | Add a test that creates a test PostgreSQL database, runs migrations, inserts test data, and verifies retrieval |
| **Benefit** | Catches migration issues, schema mismatches, query errors |
| **Risk** | Requires PostgreSQL in CI |
| **Effort** | 1-2 days |
| **Priority** | **DO BEFORE PRODUCTION LAUNCH** |

#### I23. Add Docker compose integration test (MEDIUM IMPACT, MEDIUM INVESTMENT)

| Field | Value |
|---|---|
| **Category** | Testing |
| **Current** | No test validates the full Docker compose stack |
| **Proposed** | Add a CI job that runs `docker compose up --build -d`, waits for health checks, and runs HTTP tests against all endpoints |
| **Benefit** | Catches Dockerfile bugs, env var issues, network configuration problems |
| **Risk** | CI needs Docker-in-Docker support |
| **Effort** | 2-3 days |
| **Priority** | **DO BEFORE PRODUCTION LAUNCH** |

---

## Summary of Improvement Priorities

| Priority | Items | When |
|---|---|---|
| **DO NOW** | I1, I3, I4, I6, I7, I8, I14, I15, I16, I17, I18, I21, I22, I23 | Before production launch |
| **NICE TO HAVE** | I2, I5, I9, I10, I12, I13, I19, I20 | After production launch |

---

*Report generated by automated production readiness audit — 2026-06-01*
