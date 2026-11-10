# Logistics Decision Intelligence Platform — Phase 1

## Prerequisites
- Python 3.11, Git, VS Code
- Docker Desktop with WSL 2 backend enabled

## PowerShell setup
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
docker compose up -d
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/health, http://127.0.0.1:8000/docs and http://localhost:6333/dashboard.

Verify in another PowerShell window:
```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
docker compose ps
pytest -q
```

Stop containers: `docker compose down`. To delete persisted local data too: `docker compose down -v` (destructive).

No LLM key is needed in Phase 1. `.env` is local-only; never commit it. Local database credentials are for development only.

Register the predictions router in `app/main.py` (instructions are in the chat), then start:

```powershell
uvicorn app.main:app --reload
```

Swagger: http://127.0.0.1:8000/docs
Endpoint: `POST /api/v1/predictions/transportation-cost`

Run tests: `pytest -q`

Open MLflow UI in another terminal:
`mlflow ui --backend-store-uri ./mlruns --host 127.0.0.1 --port 5000`

Then visit http://127.0.0.1:5000. All training data is synthetic; do not present its metrics as real business results.


# Warehouse Scheduling & Optimization Engine

## Goal
Use Google OR-Tools CP-SAT to assign incoming warehouse loads to docks and schedule them without overlap. The prototype minimizes priority-weighted waiting plus tardiness.

## Merge into your existing project
Copy `app/optimization/` and `app/api/routes/optimization.py` into your existing project. Merge `ortools>=9.10,<10` into your existing requirements file. Keep Phase 1 and Phase 2 files unchanged.

## Install
```powershell
pip install -r requirements-phase3.txt
```

## Run a sample optimization
```powershell
python -m app.optimization.sample_data
```

## Register the API
Add these lines to your existing `app/main.py` (do not create a second FastAPI app):
```python
from app.api.routes.optimization import router as optimization_router
app.include_router(optimization_router)
```
Then:
```powershell
uvicorn app.main:app --reload
```
Open `http://127.0.0.1:8000/docs` and try `POST /api/v1/optimization/warehouse-schedule`.

## Tests
```powershell
pytest tests/unit/test_scheduler.py -v
```

## Model explanation
- `start[i]`: start minute for load i.
- `end[i]`: completion minute for load i.
- `assign[i,d]`: Boolean indicating whether load i uses dock d.
- Optional intervals connect a load's start/end to its dock assignment.
- Exactly one dock is selected per load.
- `NoOverlap` prevents simultaneous use of the same dock.
- Objective: minimize `sum(priority[i] * (waiting[i] + tardiness[i]))`.

All times are integer minutes from the start of the planning horizon. `due_minute` is the desired completion time. Priority weights are prototype assumptions, not validated financial values. The model currently assumes interchangeable docks, no breaks, and one continuous dock occupancy per load.

## Acceptance criteria
- [ ] Sample run returns FEASIBLE or OPTIMAL.
- [ ] API endpoint appears in Swagger and returns a schedule.
- [ ] Unit tests pass.
- [ ] You can explain variables, constraints, objective, and solver status.
- [ ] Next iteration: compare against a First-Come-First-Served baseline.

Use synthetic data only; do not use confidential employer or client data.

# Logistics Intelligence Copilot

1. Activate `.venv`.
2. `pip install -r requirements-phase4.txt`
3. Copy `.env.phase4.example` entries into your existing `.env` and fill in Azure OpenAI endpoint, key, API version and deployment name.
4. Register the router in existing `app/main.py`:
   `from app.api.routes.copilot import router as copilot_router`
   `app.include_router(copilot_router)`
5. Start `uvicorn app.main:app --reload`.
6. Open `http://127.0.0.1:8000/docs`, then call `POST /api/v1/copilot/chat`.

The agent calls the existing Phase 2 and Phase 3 FastAPI endpoints over HTTP. Confirm both endpoints work independently in Swagger first.

Phase 2 payload fields assumed here: distance_km, weight_kg, volume_m3, carrier, transport_mode, origin_region, destination_region, fuel_index, urgency, month, weekend_pickup. If your actual Pydantic model differs, adjust `app/agent/tools.py`.

Use returned `thread_id` in later requests to continue a conversation. The included in-memory checkpointer is for local development only; state is lost on server restart.

This phase does not yet include RAG, SQL querying, streaming, authentication, durable checkpoints or live warehouse actions. Use synthetic data and never commit `.env`.

