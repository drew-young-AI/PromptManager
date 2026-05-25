from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProviderError(Exception):
    """Raised when a live LLM provider call fails."""


class BaseLLMProvider(ABC):
    @abstractmethod
    def is_configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def invoke(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        raise NotImplementedError


def extract_message_content(response_payload: dict[str, Any]) -> str:
    choices = response_payload.get('choices', [])
    if not choices:
        return ''

    message = choices[0].get('message', {})
    content = message.get('content', '')
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return '\n'.join(
            part.get('text', '') for part in content if isinstance(part, dict)
        ).strip()
    return str(content)