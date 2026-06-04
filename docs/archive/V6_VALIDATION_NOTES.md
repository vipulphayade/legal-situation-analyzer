# V6 Validation Notes

Main fixes applied in this package:
- section_code is now imported as subsection, eliminating duplicate section/subsection collapse.
- Startup rebuilds the dataset by default so stale rows do not survive between builds.
- The importer now stores richer metadata fields for retrieval and explanations.
- Search returns a primary bye-law plus related bye-laws with near scores.
- Clarification is now a fallback, not the first stop.
- Frontend now renders bye-law number, statement, explanation, practical guidance, and related bye-laws.
