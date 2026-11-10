from functools import lru_cache
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.models.cost_prediction.predict import load_model, predict_cost

router = APIRouter(prefix="/api/v1/predictions", tags=["predictions"])


class TransportationCostRequest(BaseModel):
    distance_km: int = Field(gt=0, le=10000)
    weight_kg: int = Field(gt=0, le=50000)
    volume_m3: float = Field(gt=0, le=200)
    carrier: str
    transport_mode: str
    origin_region: str
    destination_region: str
    fuel_index: float = Field(gt=0, le=3)
    urgency: str
    month: int = Field(ge=1, le=12)
    weekend_pickup: int = Field(ge=0, le=1)


class TransportationCostResponse(BaseModel):
    predicted_cost: float
    currency: str = "USD"
    model: str = "LightGBM"


@lru_cache(maxsize=1)
def get_model():
    return load_model()


@router.post("/transportation-cost", response_model=TransportationCostResponse)
def predict_transportation_cost(request: TransportationCostRequest):
    try:
        value = predict_cost(get_model(), request.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Prediction failed.") from exc
    return TransportationCostResponse(predicted_cost=round(value, 2))
