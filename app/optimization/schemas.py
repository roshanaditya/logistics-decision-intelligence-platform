from pydantic import BaseModel, Field, model_validator

class LoadRequest(BaseModel):
    load_id: str = Field(min_length=1)
    arrival_minute: int = Field(ge=0)
    duration_minutes: int = Field(gt=0)
    due_minute: int = Field(gt=0)
    priority: int = Field(default=1, ge=1, le=5)

    @model_validator(mode="after")
    def due_after_arrival(self):
        if self.due_minute < self.arrival_minute:
            raise ValueError("due_minute cannot be earlier than arrival_minute")
        return self

class WarehouseOptimizationRequest(BaseModel):
    loads: list[LoadRequest] = Field(min_length=1)
    dock_count: int = Field(default=6, ge=1, le=30)
    horizon_minutes: int = Field(default=1440, gt=0)
    max_solver_seconds: int = Field(default=10, ge=1, le=120)

class ScheduledLoad(BaseModel):
    load_id: str
    dock_id: int
    start_minute: int
    end_minute: int
    waiting_minutes: int
    tardiness_minutes: int
    priority: int

class WarehouseOptimizationResponse(BaseModel):
    solver_status: str
    objective_value: float | None
    total_waiting_minutes: int
    total_tardiness_minutes: int
    schedule: list[ScheduledLoad]
