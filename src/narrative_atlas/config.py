"""Environment-backed configuration with no embedded credentials."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    endpoint: str
    api_key: str
    api_version: str
    deployment: str
    max_output_tokens: int = 12_000
    temperature: float = 0.2
    request_delay: float = 1.0

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        values = {
            "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            "api_key": os.getenv("AZURE_OPENAI_API_KEY", ""),
            "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview"),
            "deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT", ""),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            names = ", ".join(name.upper() for name in missing)
            raise ValueError(f"Missing Azure OpenAI settings: {names}")
        return cls(
            **values,
            max_output_tokens=int(os.getenv("NARRATIVE_ATLAS_MAX_OUTPUT_TOKENS", "12000")),
            temperature=float(os.getenv("NARRATIVE_ATLAS_TEMPERATURE", "0.2")),
            request_delay=float(os.getenv("NARRATIVE_ATLAS_REQUEST_DELAY", "1.0")),
        )
