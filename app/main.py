from fastapi import FastAPI

app = FastAPI(
    title="Logistics Decision Intelligence Platform",
    version="0.1.0",
    description="Local development API for the Logistics Decision Intelligence Platform.",
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "logistics-decision-intelligence"}
