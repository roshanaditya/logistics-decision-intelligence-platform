# Architecture

## Phase 1
```text
Developer workstation
  +-- FastAPI application (local Python process)
  +-- Docker Compose
        +-- PostgreSQL (structured operational data; later phase)
        +-- Qdrant (vector search; later phase)
```

The initial architecture is a modular monolith. The API runs in the Python virtual environment while PostgreSQL and Qdrant run in containers.

Planned modules: `app/api`, `app/agents`, `app/rag`, `app/models`, `app/optimization`, `app/database`, `app/core`.
