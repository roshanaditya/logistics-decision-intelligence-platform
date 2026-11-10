from fastapi import FastAPI
from app.api.routes.predictions import router as predictions_router
from app.api.routes.optimization import router as optimization_router
from app.api.routes.intelligence import router as intelligence_router

app = FastAPI(
    title="LogisticsIQ",
    description="AI-Powered Logistics Decision Intelligence Platform",
    version="1.0.0",
)

app.include_router(predictions_router)
app.include_router(optimization_router)
app.include_router(intelligence_router)

@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "logistics-decision-intelligence"}

