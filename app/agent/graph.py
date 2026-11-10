from functools import lru_cache

from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from app.agent.config import get_settings
from app.agent.tools import LOGISTICS_TOOLS


SYSTEM_PROMPT = """
You are the LogisticsIQ Assistant.

You help warehouse managers and logistics teams make
better operational decisions.

Available tools:

1. predict_transportation_cost
   Predict transportation costs using the Phase 2 ML model.

2. optimize_warehouse_schedule
   Optimize warehouse dock assignments using Phase 3 OR-Tools.

Rules:
- Use tools when the user requests predictions or scheduling.
- Never fabricate tool results.
- Ask for missing information instead of guessing.
- Explain results in clear business language.
- Distinguish predictions from actual costs.
- Distinguish proposed schedules from executed actions.
"""


@lru_cache(maxsize=1)
def get_agent():

    settings = get_settings()

    if settings.llm_provider != "ollama":
        raise ValueError(
            f"Unsupported LLM provider: {settings.llm_provider}"
        )

    model = ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0,
        num_ctx=8192,
    )

    checkpointer = MemorySaver()

    agent = create_react_agent(
        model=model,
        tools=LOGISTICS_TOOLS,
        prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )

    return agent