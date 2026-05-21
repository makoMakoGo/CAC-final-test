"""LLM provider Interface."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Optional, cast

from ..config import ModelConfig


DEFAULT_PARAMS = {
    "temperature": 0.7,
    "max_tokens": 4096,
    "timeout": 300,
}


class BaseProvider(ABC):
    def __init__(self, config: ModelConfig):
        self.config = config

    def get_param(self, key: str, override: Any = None) -> Any:
        if override is not None:
            return override
        return self.config.params.get(key, DEFAULT_PARAMS.get(key))

    @abstractmethod
    def chat(self, prompt: str) -> str:
        pass

    def structured(self, request: "StructuredRequest") -> dict[str, Any]:
        return parse_structured_text(self.chat(request.text_prompt))

    def get_model_name(self) -> str:
        return self.config.name


class ToolCapableProvider(BaseProvider):
    def structured(self, request: "StructuredRequest") -> dict[str, Any]:
        return self.chat_with_tool(request.tool_prompt, request.tool_schema)

    @abstractmethod
    def chat_with_tool(self, prompt: str, tool_schema: dict[str, Any]) -> dict[str, Any]:
        pass


class StructuredRequest:
    def __init__(self, tool_prompt: str, text_prompt: str, tool_schema: dict[str, Any]):
        self.tool_prompt = tool_prompt
        self.text_prompt = text_prompt
        self.tool_schema = tool_schema


def parse_structured_text(response: str) -> dict[str, Any]:
    text = response.strip()
    fenced = _extract_fenced_json(text)
    if fenced is not None:
        text = fenced
    loaded = json.loads(text)
    if not isinstance(loaded, dict):
        raise ValueError(f"结构化输出必须是对象: {type(loaded).__name__}")
    return cast(dict[str, Any], loaded)


def _extract_fenced_json(response: str) -> Optional[str]:
    if "```json" in response:
        start = response.find("```json") + 7
        end = response.find("```", start)
        if end > start:
            return response[start:end].strip()
    if "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        if end > start:
            return response[start:end].strip()
    return None
