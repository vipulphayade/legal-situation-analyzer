# vNext Legal Guidance Architecture

Core Features:
- Hybrid retrieval
- Drift prevention
- Applicability-aware scoring
- Follow-up continuity
- Unrelated-query reset
- Explainable guidance
- Layman understanding
- Topic-aware filtering
- Reranking support
- Kubernetes scalability

Pipeline:
query
 -> query understanding
 -> topic classification
 -> vector retrieval
 -> metadata filtering
 -> reranking
 -> applicability scoring
 -> grounded prompting
 -> explainable response
