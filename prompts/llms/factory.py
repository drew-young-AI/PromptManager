from __future__ import annotations

from django.conf import settings

from .azure_openai import AzureOpenAIProvider
from .base import BaseLLMProvider
from .preview import PreviewLLMProvider

AZURE_OPENAI_PROVIDER = 'azure_openai'


def get_test_llm_provider() -> BaseLLMProvider:
    provider_name = _provider_name()
    if provider_name == AZURE_OPENAI_PROVIDER:
        provider = AzureOpenAIProvider(
            endpoint=settings.PROMPT_MANAGER_AZURE_OPENAI_ENDPOINT,
            api_key=settings.PROMPT_MANAGER_AZURE_OPENAI_API_KEY,
            deployment=settings.PROMPT_MANAGER_AZURE_OPENAI_DEPLOYMENT,
            api_version=settings.PROMPT_MANAGER_AZURE_OPENAI_API_VERSION,
            timeout_seconds=settings.PROMPT_MANAGER_TEST_TIMEOUT_SECONDS,
        )
        if provider.is_configured():
            return provider
        return PreviewLLMProvider(
            '尚未設定 Azure OpenAI 測試服務。請設定 '
            'PROMPT_MANAGER_AZURE_OPENAI_ENDPOINT、'
            'PROMPT_MANAGER_AZURE_OPENAI_API_KEY 與 '
            'PROMPT_MANAGER_AZURE_OPENAI_DEPLOYMENT，才能將提示詞送到模型服務測試。'
        )

    return PreviewLLMProvider(
        f'不支援的 LLM provider：「{provider_name}」。目前僅支援 azure_openai。'
    )


def is_test_llm_configured() -> bool:
    provider_name = _provider_name()
    if provider_name != AZURE_OPENAI_PROVIDER:
        return False

    provider = AzureOpenAIProvider(
        endpoint=settings.PROMPT_MANAGER_AZURE_OPENAI_ENDPOINT,
        api_key=settings.PROMPT_MANAGER_AZURE_OPENAI_API_KEY,
        deployment=settings.PROMPT_MANAGER_AZURE_OPENAI_DEPLOYMENT,
        api_version=settings.PROMPT_MANAGER_AZURE_OPENAI_API_VERSION,
        timeout_seconds=settings.PROMPT_MANAGER_TEST_TIMEOUT_SECONDS,
    )
    return provider.is_configured()


def _provider_name() -> str:
    return str(getattr(settings, 'PROMPT_MANAGER_LLM_PROVIDER', AZURE_OPENAI_PROVIDER) or '').strip().lower()