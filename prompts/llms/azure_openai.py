from __future__ import annotations

import json
from typing import Any
from urllib import error, parse, request

from .base import BaseLLMProvider, LLMProviderError, extract_message_content


class AzureOpenAIProvider(BaseLLMProvider):
    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        deployment: str,
        api_version: str,
        timeout_seconds: int,
    ):
        self.endpoint = str(endpoint or '').strip()
        self.api_key = str(api_key or '').strip()
        self.deployment = str(deployment or '').strip()
        self.api_version = str(api_version or '').strip()
        self.timeout_seconds = int(timeout_seconds)

    def is_configured(self) -> bool:
        return bool(self.endpoint and self.api_key and self.deployment and self.api_version)

    def invoke(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        if not self.is_configured():
            raise LLMProviderError(
                'Azure OpenAI 尚未設定完成。請設定 endpoint、api key、deployment 與 api version。'
            )

        payload = json.dumps({'messages': messages}).encode('utf-8')
        provider_request = request.Request(
            self._build_request_url(),
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'api-key': self.api_key,
            },
            method='POST',
        )

        try:
            with request.urlopen(
                provider_request,
                timeout=self.timeout_seconds,
            ) as response:
                raw_response = response.read().decode('utf-8')
        except error.HTTPError as exc:
            detail = exc.read().decode('utf-8', errors='replace')
            raise LLMProviderError(f'Azure OpenAI 回傳 HTTP {exc.code}：{detail}') from exc
        except error.URLError as exc:
            raise LLMProviderError(f'無法連線到 Azure OpenAI：{exc.reason}') from exc

        parsed_response = json.loads(raw_response or '{}')
        return {
            'mode': 'live',
            'output': extract_message_content(parsed_response),
            'provider_response': parsed_response,
        }

    def _build_request_url(self) -> str:
        normalized_endpoint = self.endpoint.rstrip('/')
        if '/openai/deployments/' in normalized_endpoint:
            return self._append_api_version(normalized_endpoint)

        deployment = parse.quote(self.deployment, safe='')
        return self._append_api_version(
            f'{normalized_endpoint}/openai/deployments/{deployment}/chat/completions'
        )

    def _append_api_version(self, url: str) -> str:
        separator = '&' if '?' in url else '?'
        if 'api-version=' in url:
            return url
        return f'{url}{separator}api-version={parse.quote(self.api_version, safe="")}'