
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent.graph import get_agent

router = APIRouter(
    prefix="/api/v1/intelligence",
    tags=["Intelligence"]
)


class IntelligenceQueryRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    thread_id: str | None = None


class IntelligenceQueryResponse(BaseModel):
    thread_id: str
    answer: str


@router.post(
    "/query",
    response_model=IntelligenceQueryResponse
)
def query_logistics_intelligence(
    request: IntelligenceQueryRequest
):
    thread_id = request.thread_id or str(uuid4())

    try:
        result = get_agent().invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": request.message
                    }
                ]
            },
            config={
                "configurable": {
                    "thread_id": thread_id
                }
            }
        )

        for msg in reversed(result.get("messages", [])):
            if getattr(msg, "type", None) == "ai" and getattr(msg, "content", None):
                content = msg.content

                if isinstance(content, str):
                    answer = content
                else:
                    answer = str(content)

                return IntelligenceQueryResponse(
                    thread_id=thread_id,
                    answer=answer
                )

        return IntelligenceQueryResponse(
            thread_id=thread_id,
            answer="No text response was returned."
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"LogisticsIQ request failed "
                f"({type(exc).__name__}): {str(exc)[:400]}"
            )
        ) from exc