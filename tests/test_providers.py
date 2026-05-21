import pytest

from cac.config import ModelConfig
from cac.providers import create_provider
from cac.providers.base import BaseProvider, StructuredRequest, parse_structured_text
from cac.providers.custom import CustomProvider
from cac.providers.openai import OpenAIProvider


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


def test_custom_provider_is_separate_adapter_with_full_url() -> None:
    provider = create_provider(_model_config("custom"))

    assert isinstance(provider, CustomProvider)
    assert provider.chat_url() == "https://api.example.test/v1"


def test_openai_provider_builds_chat_completions_url() -> None:
    provider = create_provider(_model_config("openai"))

    assert isinstance(provider, OpenAIProvider)
    assert provider.chat_url() == "https://api.example.test/v1/chat/completions"


def test_structured_text_parser_accepts_fenced_json() -> None:
    assert parse_structured_text('```json\n{"total_score": 1}\n```') == {"total_score": 1}


class TextOnlyProvider(BaseProvider):
    def chat(self, prompt: str) -> str:
        assert prompt == "text prompt"
        return '{"ok": true}'


def test_text_provider_structured_uses_text_prompt() -> None:
    provider = TextOnlyProvider(_model_config("custom"))
    request = StructuredRequest(
        tool_prompt="tool prompt",
        text_prompt="text prompt",
        tool_schema={"name": "submit_score", "parameters": {}},
    )

    assert provider.structured(request) == {"ok": True}
