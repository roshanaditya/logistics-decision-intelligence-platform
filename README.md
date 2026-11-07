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
