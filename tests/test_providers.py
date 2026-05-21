import pytest

from src.config import ModelConfig
from src.providers import create_provider
from src.providers.base import BaseProvider
from src.providers.openai import OpenAIProvider


def _model_config(provider: str) -> ModelConfig:
    return ModelConfig(
        name="demo",
        provider=provider,
        api_key="key",
        base_url="https://api.example.test/v1",
        model_id="demo",
    )


def test_create_provider_returns_registered_provider() -> None:
    provider = create_provider(_model_config("openai"))

    assert isinstance(provider, OpenAIProvider)
    assert isinstance(provider, BaseProvider)
    assert provider.get_model_name() == "demo"


def test_create_provider_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="不支持的 provider: unknown"):
        create_provider(_model_config("unknown"))


def test_custom_openai_provider_disables_tool_calling() -> None:
    provider = create_provider(_model_config("custom"))

    assert isinstance(provider, OpenAIProvider)
    assert provider.supports_tool_calling() is False
