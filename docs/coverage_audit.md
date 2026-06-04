# Dataset Coverage and Legal Completeness Audit

**Audit Date:** 2026-06-02
**Source:** mysocietyclub.com detail pages (verbatim) vs current dataset (239 records)

---

## Coverage Scores

| Category | Score | Risk | Primary Impact |
|---|---|---|---|
| **A. Structural Coverage** | 8/10 | LOW | Retrieval |
| **B. Legal Coverage** | 2/10 | HIGH | Answer Quality |
| **C. Retrieval Coverage** | 6/10 | MEDIUM | Retrieval |
| **D. Answer Coverage** | 4/10 | HIGH | Answer Quality |
| **E. Follow-up Coverage** | 3/10 | HIGH | Follow-up Quality |
| **F. Special Content** | 1/10 | HIGH | Answer Quality |

---

## Category Breakdown

### A. Structural Coverage — 8/10
- 175/175 bylaw numbers present ✓
- 93/239 records (39%) use subsection codes ✓ (post-repair)
- 20 unique chapters matching source ✓
- **Gap:** 6 chapter source pages returned 404 during audit (XIII–XIX: Appropriation of Profits, Books of Account, Audit, Complaints, Redevelopment, Write-off). Their 26 records are entirely AI-derived.
- **Gap:** Source URL has space typo (`mysocietyclub. com`) in all 229 original records.

### B. Legal Coverage — 2/10
- Only **12/239 (5%)** records contain verbatim legal text from source
- **227/239 (95%)** are AI-derived fallback with generic, non-authoritative text
- Structured data fields for legal specifics are virtually empty:
  - Eligibility requirements: **0/239**
  - Quorum requirements: **0/239**
  - Date references: **0/239**
  - Percentage/fraction rules: **0/239**
  - Voting thresholds: **3/239** (1.3%)
  - Time limits: **6/239** (2.5%)
  - Approval requirements: **5/239** (2.1%)
  - Penalty conditions: **2/239** (0.8%)
  - Financial limits: **2/239** (0.8%)
- Conditions, exceptions, and procedures from source pages are not extracted into machine-readable form.

### C. Retrieval Coverage — 6/10
- All records have keywords, technical_terms, actor_types, topic groups ✓
- Retrieval works at structural level (bylaw numbers, topics) ✓
- **Gap:** Keywords are AI-generated and may not match real user vocabulary
- **Gap:** Synonyms and alternative phrasings are not systematically curated
- **Gap:** 162/229 (70.7%) original records lacked source-verified content → retrieval text is AI-derived generic

### D. Answer Coverage — 4/10
- 100% field fill rate for plain_english, detailed_explanation, member_rights, committee_obligations, action_steps, documents_to_check **BUT** all AI-derived
- **Gap:** Explanations are generic templates, not grounded in actual legal text:
  - Pattern: *"This bye-law governs [title]. It applies when..."* — same template for all 227 AI records
  - No variation or specificity by bylaw content
- **Gap:** Conditions, exceptions, and qualifying clauses from source are absent from explanations

### E. Follow-up Coverage — 3/10
- All records have related_bylaws and followup_questions ✓
- **Gap:** Related_by-laws are AI-generated similarity links, not source-grounded cross-references
- **Gap:** Follow-up questions are generic (*"What part of the clause or record is disputed?"*) — not tailored to the bylaw's specific content
- **Gap:** No source-verified cross-reference graph exists

### F. Special Content Coverage — 1/10
- Tables: **0** (source has committee strength tables, fee structures, form appendices)
- Forms: **2** references found (not extracted content)
- Schedules: **1** reference found
- Annexures: **0**
- Fee structures: **4** references found (not extracted data)
- Source appendix forms (FORM J-1, Indemnity Bond, etc.) are mentioned in legal text but not present as structured data

---

## High Priority Gaps

| # | Gap | Impact | Recommendation |
|---|---|---|---|
| 1 | **95% AI-derived legal text** — only 12/239 records have verbatim source text | Answer Quality critically degraded; system cannot provide authoritative legal answers | Prioritize verbatim source extraction for all 227 remaining records. Target: mysocietyclub.com detail pages (one fetch per page covers 5–15 records). Do NOT re-scrape; fetch per-chapter pages. |
| 2 | **Structured legal data empty** — 0/239 for eligibility, quorum, percentages, dates | Legal reasoning impossible; system cannot compute eligibility, voting validity, or deadlines | Extract structured conditions from source text. Start with high-frequency query topics: elections (115), membership (22), meetings (100–109), charges (65–71). |
| 3 | **6 unverifiable source chapters** — 26 records with no source page to verify against | These chapters' content cannot be trusted for any legal answer | Investigate if source pages moved or were restructured. Try alternative URLs or archive.org. If permanently unavailable, flag these 26 records explicitly. |
| 4 | **No table/list content extracted** — committee strength table, fee schedules, form formats | Answers about specific numeric thresholds, fees, or form requirements will be wrong | Extract tables from source pages for chapters that have them (XII committee table, IX charges, XIII registers). Prioritize the committee strength table (bylaw 114). |

## Medium Priority Gaps

| # | Gap | Impact | Recommendation |
|---|---|---|---|
| 5 | **Related_by-laws are AI-generated similarities, not source cross-references** | Follow-up recommendations may point to irrelevant or weakly linked bylaws | Build a curated cross-reference graph from source text mentions (e.g., "as provided under bye-law No. 65"). Already ~20% of records have such mentions in their legal text. |
| 6 | **Follow-up questions are generic templates** | User gets same 1–2 questions regardless of bylaw | Generate bylaw-specific follow-ups from actual conditions and exceptions. |
| 7 | **Keywords lack synonyms and user vocabulary** | Users searching with common phrases may get low semantic match | Add synonym curation for top 20 query intents, not full re-generation. |

## Low Priority Gaps

| # | Gap | Impact | Recommendation |
|---|---|---|---|
| 8 | **Source URL typo (space)** | Cosmetic; no functional impact | Batch-fix on next write. |
| 9 | **9 chapter names differ from source** | Cosmetic; retrieval uses `topic_group` not `chapter` | Update chapter names to match source for consistency. |
| 10 | **Forms, schedules, annexures absent** | Low query frequency; retrieval still finds bylaw by number | Add as structured data when the containing chapters are re-sourced. |

---

## Recommended Dataset Improvements (Ranked)

1. **Fetch verbatim text for 227 remaining records** from source pages (6–8 page fetches cover all). This is the single highest-impact change.
2. **Extract structured conditions** from the 12 already-verbatim records (byelaws 22, 46, 115) as a model for the rest.
3. **Build source-grounded cross-reference index** from "as provided under bye-law No. X" mentions.
4. **Extract tables** starting with committee strength (114), voting thresholds (106), and fee schedules (65–71).
5. **Add synonym curation** for top-20 query terms from benchmark failures.
6. **Flag 26 unverifiable records** explicitly in metadata.

## Verdict

The dataset has **excellent structural coverage** (all bylaw numbers, all chapters, all relational metadata) but **critically insufficient legal content coverage**. The system's answers are currently built on AI-generated templates with no authoritative grounding for 95% of records. Retrieval works at the bylaw-number level, but **answer quality and legal accuracy cannot be trusted** until verbatim legal text is ingested.

**Do NOT re-scrape.** The source pages are accessible (except chapters XIII–XIX which need URL investigation). Fetch the 6–8 remaining chapter pages to cover all 227 records.
