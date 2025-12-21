"""Azure OpenAI adapter and resilient structured extraction loop."""

from __future__ import annotations

import logging
import time
from typing import Any, Protocol

from openai import AzureOpenAI

from .config import Settings
from .parsing import appears_truncated, parse_json_items

LOGGER = logging.getLogger(__name__)


class CompletionClient(Protocol):
    def complete(self, system_prompt: str, user_prompt: str) -> str: ...


class AzureCompletionClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = AzureOpenAI(
            api_key=settings.api_key,
            api_version=settings.api_version,
            azure_endpoint=settings.endpoint,
        )

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        kwargs: dict[str, Any] = {
            "model": self.settings.deployment,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.settings.temperature,
        }
        token_parameter = (
            "max_completion_tokens"
            if "gpt-5" in self.settings.deployment.casefold()
            else "max_tokens"
        )
        kwargs[token_parameter] = self.settings.max_output_tokens
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or "[]"


class ResilientExtractor:
    """Retries invalid responses and requests continuations for truncated arrays."""

    def __init__(self, client: CompletionClient, *, request_delay: float = 1.0):
        self.client = client
        self.request_delay = request_delay

    def extract(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        identity_key: str = "name",
        retries: int = 3,
        continuation_rounds: int = 4,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        identities: set[str] = set()
        prompt = user_prompt

        for _continuation in range(continuation_rounds):
            content = ""
            parsed: list[dict[str, Any]] = []
            for attempt in range(retries):
                try:
                    content = self.client.complete(system_prompt, prompt)
                    parsed = parse_json_items(content)
                    if parsed or content.strip() == "[]":
                        break
                except Exception as error:
                    if attempt + 1 == retries:
                        raise
                    wait = 5 * (2**attempt) if "429" in str(error) else 2**attempt
                    LOGGER.warning("Completion failed; retrying in %ss: %s", wait, error)
                    time.sleep(wait)
                prompt = user_prompt + "\n\nReturn only a syntactically valid JSON array."

            new_count = 0
            for item in parsed:
                identity = " ".join(str(item.get(identity_key, item)).casefold().split())
                if identity not in identities:
                    identities.add(identity)
                    items.append(item)
                    new_count += 1

            if not appears_truncated(content) or new_count == 0:
                break
            sample = ", ".join(sorted(identities)[:15])
            prompt = (
                user_prompt
                + "\n\nThe previous JSON array was truncated. Continue with a fresh JSON array. "
                + f"Do not repeat these items: {sample}."
            )
            time.sleep(self.request_delay)
        return items
