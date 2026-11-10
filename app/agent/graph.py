"""LogisticsIQ hybrid orchestration graph.

The LLM extracts intent and inputs. Python validates the plan and enforces
execution of every requested backend capability. The LLM explains verified
results; it does not decide whether mandatory operations execute.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any, Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.agent.config import get_settings
from app.agent.tools import (
    optimize_warehouse_schedule,
    predict_transportation_cost,
)


class RequestPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")
    prediction_requested: bool = False
    optimization_requested: bool = False
    prediction_inputs: dict[str, Any] = Field(default_factory=dict)
    optimization_inputs: dict[str, Any] = Field(default_factory=dict)


class LogisticsState(TypedDict, total=False):
    messages: Annotated[list[Any], add_messages]
    plan: dict[str, Any]
    missing_information: list[str]
    planning_error: str
    results: dict[str, Any]
    answer: str


PREDICTION_FIELDS = (
    "distance_km", "weight_kg", "volume_m3", "carrier", "transport_mode",
    "origin_region", "destination_region", "fuel_index", "urgency", "month",
    "weekend_pickup",
)
LOAD_FIELDS = ("load_id", "arrival_minute", "duration_minutes", "due_minute")


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(part.get("text", "")) if isinstance(part, dict) else str(part)
            for part in content
        )
    return str(content)


def _user_context(messages: list[Any]) -> str:
    # Do not use previous assistant messages as a source of operational inputs.
    user_messages = [
        _text(m.content) for m in messages
        if getattr(m, "type", None) == "human"
    ]
    return "\n\n".join(user_messages[-8:])


def _json_object(raw: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Model did not return a JSON object")
        value = json.loads(cleaned[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_prediction(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for field in PREDICTION_FIELDS:
        if field not in data or data[field] is None or data[field] == "":
            issues.append(f"Transportation prediction: {field}")

    if issues:
        return issues

    for field in ("distance_km", "weight_kg", "volume_m3", "fuel_index"):
        value = data[field]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            issues.append(f"Transportation prediction: {field} must be numeric")

    for field in ("distance_km", "weight_kg", "fuel_index"):
        value = data[field]
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value <= 0:
            issues.append(f"Transportation prediction: {field} must be greater than 0")

    if isinstance(data["volume_m3"], (int, float)) and data["volume_m3"] < 0:
        issues.append("Transportation prediction: volume_m3 cannot be negative")

    if not _is_int(data["month"]) or not 1 <= data["month"] <= 12:
        issues.append("Transportation prediction: month must be an integer from 1 to 12")

    if not isinstance(data["weekend_pickup"], bool):
        issues.append("Transportation prediction: weekend_pickup must be true or false")

    for field in ("carrier", "transport_mode", "origin_region",
                  "destination_region", "urgency"):
        if not isinstance(data[field], str) or not data[field].strip():
            issues.append(f"Transportation prediction: {field} must be a non-empty string")
    return issues


def _validate_optimization(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    loads = data.get("loads")
    if not isinstance(loads, list) or not loads:
        issues.append("Warehouse optimization: provide a non-empty loads list")
    else:
        for i, load in enumerate(loads, start=1):
            if not isinstance(load, dict):
                issues.append(f"Warehouse optimization: load {i} must be an object")
                continue
            for field in LOAD_FIELDS:
                if load.get(field) is None or load.get(field) == "":
                    issues.append(f"Warehouse optimization: load {i} is missing {field}")
            for field in ("arrival_minute", "duration_minutes", "due_minute"):
                value = load.get(field)
                if value is not None and not _is_int(value):
                    issues.append(f"Warehouse optimization: load {i} {field} must be an integer")
            if _is_int(load.get("arrival_minute")) and load["arrival_minute"] < 0:
                issues.append(f"Warehouse optimization: load {i} arrival_minute cannot be negative")
            if _is_int(load.get("duration_minutes")) and load["duration_minutes"] <= 0:
                issues.append(f"Warehouse optimization: load {i} duration_minutes must be positive")
            if _is_int(load.get("due_minute")) and load["due_minute"] < 0:
                issues.append(f"Warehouse optimization: load {i} due_minute cannot be negative")

    # Require operational constraints explicitly; do not silently use business defaults.
    for field in ("dock_count", "horizon_minutes"):
        value = data.get(field)
        if not _is_int(value) or value <= 0:
            issues.append(f"Warehouse optimization: {field} must be a positive integer")

    solver_limit = data.get("max_solver_seconds", 10)
    if not _is_int(solver_limit) or solver_limit <= 0:
        issues.append("Warehouse optimization: max_solver_seconds must be a positive integer")
    return issues


def _decode_result(raw: Any) -> tuple[bool, Any]:
    if isinstance(raw, str):
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            result = raw
    else:
        result = raw
    if isinstance(result, dict) and (result.get("success") is False or result.get("error")):
        return False, result
    return True, result


def _make_nodes(model: ChatOllama):
    def understand_request(state: LogisticsState) -> dict[str, Any]:
        context = _user_context(state.get("messages", []))
        prompt = f"""
Extract intent and explicitly supplied values from the user conversation.
Return ONLY valid JSON with this exact structure:
{{
  "prediction_requested": false,
  "optimization_requested": false,
  "prediction_inputs": {{
    "distance_km": null, "weight_kg": null, "volume_m3": null,
    "carrier": null, "transport_mode": null, "origin_region": null,
    "destination_region": null, "fuel_index": null, "urgency": null,
    "month": null, "weekend_pickup": null
  }},
  "optimization_inputs": {{
    "loads": [], "dock_count": null, "horizon_minutes": null,
    "max_solver_seconds": 10
  }}
}}
Rules:
- Set prediction_requested true for a transportation-cost prediction request.
- Set optimization_requested true for a warehouse scheduling/optimization request.
- Set both true when both operations are requested.
- Extract only values explicitly supplied by the user. Never guess or infer missing business inputs.
- Only user messages are included below; do not invent values.
- Convert an unambiguous month name to an integer from 1 to 12.
- weekend_pickup must be a boolean only when clearly stated.
- Each load requires load_id, arrival_minute, duration_minutes, due_minute;
  priority is optional.
- Use null or an empty list for missing values. Do not add prose or markdown.

USER CONVERSATION:
{context}
"""
        try:
            response = model.invoke([
                SystemMessage(content="You are a structured request extractor. Return JSON only."),
                HumanMessage(content=prompt),
            ])
            plan = RequestPlan.model_validate(_json_object(_text(response.content)))
            return {"plan": plan.model_dump(), "planning_error": ""}
        except (ValueError, ValidationError, json.JSONDecodeError):
            return {
                "plan": {},
                "planning_error": (
                    "I could not reliably extract the requested operation and its inputs. "
                    "Please restate the request with the required details."
                ),
            }
        except Exception:
            return {
                "plan": {},
                "planning_error": "Request understanding is temporarily unavailable. Please try again.",
            }

    def validate_inputs(state: LogisticsState) -> dict[str, Any]:
        plan = state.get("plan", {})
        missing: list[str] = []
        if plan.get("prediction_requested"):
            missing.extend(_validate_prediction(plan.get("prediction_inputs") or {}))
        if plan.get("optimization_requested"):
            missing.extend(_validate_optimization(plan.get("optimization_inputs") or {}))
        return {"missing_information": missing}

    def execute_requested_tools(state: LogisticsState) -> dict[str, Any]:
        plan = state.get("plan", {})
        results: dict[str, Any] = {}

        # Mandatory tool execution is controlled by Python, not by an LLM tool-call choice.
        if plan.get("prediction_requested"):
            try:
                raw = predict_transportation_cost.invoke(plan["prediction_inputs"])
                ok, output = _decode_result(raw)
                results["transportation_cost_prediction"] = {
                    "status": "success" if ok else "failed",
                    "source": "/api/v1/predictions/transportation-cost",
                    "output": output,
                }
            except Exception as exc:
                results["transportation_cost_prediction"] = {
                    "status": "failed",
                    "source": "/api/v1/predictions/transportation-cost",
                    "error": f"{type(exc).__name__}: {str(exc)[:500]}",
                }

        if plan.get("optimization_requested"):
            try:
                inputs = dict(plan["optimization_inputs"])
                inputs.setdefault("max_solver_seconds", 10)
                raw = optimize_warehouse_schedule.invoke(inputs)
                ok, output = _decode_result(raw)
                results["warehouse_schedule_optimization"] = {
                    "status": "success" if ok else "failed",
                    "source": "/api/v1/optimization/warehouse-schedule",
                    "output": output,
                }
            except Exception as exc:
                results["warehouse_schedule_optimization"] = {
                    "status": "failed",
                    "source": "/api/v1/optimization/warehouse-schedule",
                    "error": f"{type(exc).__name__}: {str(exc)[:500]}",
                }
        return {"results": results}

    def generate_response(state: LogisticsState) -> dict[str, Any]:
        if state.get("planning_error"):
            answer = state["planning_error"]
            return {"answer": answer, "messages": [AIMessage(content=answer)]}

        plan = state.get("plan", {})
        missing = state.get("missing_information", [])
        if missing:
            answer = (
                "I need a few more details before I can run the requested operation:\n\n"
                + "\n".join(f"- {item}" for item in missing)
                + "\n\nPlease provide these details. I have not executed the requested "
                  "prediction or optimization yet."
            )
            return {"answer": answer, "messages": [AIMessage(content=answer)]}

        if not plan.get("prediction_requested") and not plan.get("optimization_requested"):
            response = model.invoke([
                SystemMessage(content=(
                    "You are LogisticsIQ, a logistics decision-intelligence assistant. "
                    "Answer general questions. Do not claim that a prediction or "
                    "optimization was run unless this workflow provides its result."
                )),
                HumanMessage(content=_user_context(state.get("messages", []))),
            ])
            answer = _text(response.content)
            return {"answer": answer, "messages": [AIMessage(content=answer)]}

        result_json = json.dumps(state.get("results", {}), ensure_ascii=False, default=str)
        response = model.invoke([
            SystemMessage(content=(
                "You explain LogisticsIQ execution results. Use only the supplied "
                "execution payload. Never invent or reuse a cost, schedule, metric, "
                "feature contribution, dock assignment, or solver status. Only a "
                "result with status='success' is usable. For status='failed', state "
                "that the operation failed and do not provide a substitute result. "
                "Distinguish predicted costs from actual invoice costs and proposed "
                "schedules from executed actions. Do not claim the prediction affected "
                "the schedule unless the payload explicitly says so."
            )),
            HumanMessage(content=(
                "Explain these execution results in business language. Keep each "
                "capability's result separate.\n\nEXECUTION RESULTS:\n" + result_json
            )),
        ])
        answer = _text(response.content)
        return {"answer": answer, "messages": [AIMessage(content=answer)]}

    return understand_request, validate_inputs, execute_requested_tools, generate_response


@lru_cache(maxsize=1)
def get_agent():
    settings = get_settings()
    if settings.llm_provider != "ollama":
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")

    model = ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0,
        num_ctx=8192,
    )

    understand, validate, execute, respond = _make_nodes(model)

    workflow = StateGraph(LogisticsState)
    workflow.add_node("understand_request", understand)
    workflow.add_node("validate_inputs", validate)
    workflow.add_node("execute_requested_tools", execute)
    workflow.add_node("generate_response", respond)

    workflow.add_edge(START, "understand_request")
    workflow.add_edge("understand_request", "validate_inputs")

    def after_validation(state: LogisticsState) -> str:
        if state.get("planning_error") or state.get("missing_information"):
            return "generate_response"
        plan = state.get("plan", {})
        if not plan.get("prediction_requested") and not plan.get("optimization_requested"):
            return "generate_response"
        return "execute_requested_tools"

    workflow.add_conditional_edges(
        "validate_inputs",
        after_validation,
        {
            "generate_response": "generate_response",
            "execute_requested_tools": "execute_requested_tools",
        },
    )
    workflow.add_edge("execute_requested_tools", "generate_response")
    workflow.add_edge("generate_response", END)

    # Preserve the existing thread_id-based API and in-memory conversation state.
    return workflow.compile(checkpointer=MemorySaver())
