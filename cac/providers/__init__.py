"""Provider registry."""

from __future__ import annotations

from typing import Type

from ..config import ModelConfig
from .anthropic import AnthropicProvider
from .base import BaseProvider, StructuredRequest, ToolCapableProvider
from .custom import CustomProvider
from .gemini import GeminiProvider
from .openai import OpenAIProvider


PROVIDER_REGISTRY: dict[str, Type[BaseProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "custom": CustomProvider,
    "doubao": OpenAIProvider,
}


def create_provider(config: ModelConfig) -> BaseProvider:
    provider_type = config.provider.lower()
    if provider_type not in PROVIDER_REGISTRY:
        raise ValueError(f"不支持的 provider: {config.provider}")
    return PROVIDER_REGISTRY[provider_type](config)


__all__ = [
    "BaseProvider",
    "ToolCapableProvider",
    "StructuredRequest",
    "OpenAIProvider",
    "CustomProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "create_provider",
    "PROVIDER_REGISTRY",
]
