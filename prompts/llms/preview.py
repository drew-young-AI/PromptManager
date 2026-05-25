from __future__ import annotations

from typing import Any

from .base import BaseLLMProvider


class PreviewLLMProvider(BaseLLMProvider):
    def __init__(self, message: str):
        self.message = message

    def is_configured(self) -> bool:
        return False

    def invoke(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        return {
            'mode': 'preview',
            'output': self.message,
            'provider_response': None,
        }