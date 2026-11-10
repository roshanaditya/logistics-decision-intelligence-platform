
import json
from typing import Any

import httpx
from langchain_core.tools import tool

from app.agent.config import get_settings


def _post_to_app(path: str, payload: dict[str, Any]) -> str:
    """Send a POST request to an internal LogisticsIQ API endpoint."""

    url = f"{get_settings().app_api_base_url}{path}"

    try:
        response = httpx.post(
            url,
            json=payload,
            timeout=60.0
        )
        response.raise_for_status()

        return json.dumps(
            response.json(),
            ensure_ascii=False
        )

    except httpx.HTTPStatusError as exc:
        return json.dumps({
            "success": False,
            "error": "Backend HTTP error",
            "status_code": exc.response.status_code,
            "detail": exc.response.text[:1200]
        })

    except httpx.RequestError as exc:
        return json.dumps({
            "success": False,
            "error": "Could not connect to application API",
            "detail": str(exc),
            "hint": "Check Uvicorn and APP_API_BASE_URL."
        })


@tool
def predict_transportation_cost(
    distance_km: float,
    weight_kg: float,
    volume_m3: float,
    carrier: str,
    transport_mode: str,
    origin_region: str,
    destination_region: str,
    fuel_index: float,
    urgency: str,
    month: int,
    weekend_pickup: bool
) -> str:
    """
    Predict transportation cost using the Phase 2 LightGBM model.

    Requires all shipment features.
    Ask the user for missing information.
    Never invent shipment input values.
    The result is a model prediction, not an actual invoice cost.
    """

    payload = {
        "distance_km": distance_km,
        "weight_kg": weight_kg,
        "volume_m3": volume_m3,
        "carrier": carrier,
        "transport_mode": transport_mode,
        "origin_region": origin_region,
        "destination_region": destination_region,
        "fuel_index": fuel_index,
        "urgency": urgency,
        "month": month,
        "weekend_pickup": weekend_pickup
    }

    return _post_to_app(
        "/api/v1/predictions/transportation-cost",
        payload
    )


@tool
def optimize_warehouse_schedule(
    loads: list[dict[str, Any]],
    dock_count: int = 6,
    horizon_minutes: int = 1440,
    max_solver_seconds: int = 10
) -> str:
    """
    Propose an optimized warehouse dock schedule using Phase 3 CP-SAT.

    Each load requires:
    load_id, arrival_minute, duration_minutes, due_minute.
    Priority is optional if supported by the API.

    The result is a proposed schedule, not an executed warehouse action.
    """

    payload = {
        "loads": loads,
        "dock_count": dock_count,
        "horizon_minutes": horizon_minutes,
        "max_solver_seconds": max_solver_seconds
    }

    return _post_to_app(
        "/api/v1/optimization/warehouse-schedule",
        payload
    )


LOGISTICS_TOOLS = [
    predict_transportation_cost,
    optimize_warehouse_schedule
]
