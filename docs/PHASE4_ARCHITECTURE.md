# Phase 4.1 architecture

Client -> FastAPI `/api/v1/copilot/chat` -> LangGraph ReAct agent -> Azure OpenAI.
The model can select typed tools. Each tool calls an existing Phase 2 or Phase 3 endpoint
over HTTP, then the model explains the returned result.

HTTP integration keeps service boundaries clear and avoids coupling the agent to model internals.
`MemorySaver` is process-local development memory only. Replace it with a durable checkpointer
before multi-worker/production use.

Safety: tools only predict and propose schedules. They do not dispatch loads or mutate live
warehouse systems. Any future write action needs authentication, authorization, audit logging,
idempotency and explicit human approval.

Verify the actual Phase 2 request schema against `tools.py`; its feature field names are an
assumption based on the synthetic dataset used in Phase 2.
