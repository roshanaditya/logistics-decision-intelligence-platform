import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class AgentSettings:
    llm_provider: str
    ollama_base_url: str
    ollama_model: str
    app_api_base_url: str


def get_settings() -> AgentSettings:
    return AgentSettings(
        llm_provider=os.getenv("LLM_PROVIDER", "ollama").lower(),
        ollama_base_url=os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        ),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen3:8b"),
        app_api_base_url=os.getenv(
            "APP_API_BASE_URL", "http://127.0.0.1:8000"
        ).rstrip("/"),
    )