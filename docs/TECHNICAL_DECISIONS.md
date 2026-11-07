# Technical Decision Records

## ADR-001: Modular monolith
Decision: one Python codebase with clear module boundaries.
Rationale: reduces deployment/debugging overhead for an initial solo project. Split services only when independent scaling or deployment is justified.

## ADR-002: Docker Compose for infrastructure
Decision: PostgreSQL and Qdrant run in containers; API runs in the Python virtual environment.
Rationale: reproducible dependencies with a fast application debugging loop.

## ADR-003: Hosted LLM APIs later
Decision: use an API-based provider in a later phase; no local model server in Phase 1.
Rationale: avoid GPU/model-serving complexity while establishing the application foundation.
