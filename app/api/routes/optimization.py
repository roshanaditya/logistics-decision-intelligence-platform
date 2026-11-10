from fastapi import APIRouter, HTTPException
from app.optimization.scheduler import optimize_warehouse_schedule
from app.optimization.schemas import WarehouseOptimizationRequest, WarehouseOptimizationResponse

router = APIRouter(prefix="/api/v1/optimization", tags=["Warehouse Optimization"])

@router.post("/warehouse-schedule", response_model=WarehouseOptimizationResponse)
def create_warehouse_schedule(request: WarehouseOptimizationRequest):
    try:
        return optimize_warehouse_schedule(
            loads=request.loads, dock_count=request.dock_count,
            horizon_minutes=request.horizon_minutes,
            max_solver_seconds=request.max_solver_seconds)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
