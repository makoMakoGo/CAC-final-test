"""Anthropic provider Adapter."""

from __future__ import annotations

from typing import Any, cast

import requests

from .base import ToolCapableProvider


class AnthropicProvider(ToolCapableProvider):
    def chat_with_tool(self, prompt: str, tool_schema: dict[str, Any]) -> dict[str, Any]:
        tool_def = {
            "name": tool_schema["name"],
            "description": tool_schema.get("description", ""),
            "input_schema": tool_schema["parameters"],
        }
        data = {
            "model": self.config.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.get_param("max_tokens"),
            "temperature": self.get_param("temperature"),
            "tools": [tool_def],
            "tool_choice": {"type": "tool", "name": tool_schema["name"]},
        }
        response = requests.post(
            self.messages_url(),
            headers=self._headers(),
            json=data,
            timeout=self.get_param("timeout"),
        )
        response.raise_for_status()
        result = response.json()
        for item in result["content"]:
            if isinstance(item, dict) and item.get("type") == "tool_use":
                return cast(dict[str, Any], item["input"])
        raise ValueError("Anthropic 响应中未找到 tool_use 块")

    def chat(self, prompt: str) -> str:
        data: dict[str, Any] = {
            "model": self.config.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.get_param("max_tokens"),
            "temperature": self.get_param("temperature"),
        }
        for param in ["top_p", "top_k", "stop_sequences"]:
            value = self.config.params.get(param)
            if value is not None:
                data[param] = value

        response = requests.post(
            self.messages_url(),
            headers=self._headers(),
            json=data,
            timeout=self.get_param("timeout"),
        )
        response.raise_for_status()
        result = response.json()

        thinking_content = ""
        text_content = ""
        for item in result["content"]:
            if isinstance(item, dict):
                item_type = item.get("type", "")
                if item_type == "thinking":
                    thinking_content = item.get("thinking", "")
                elif item_type == "text":
                    text_content = item.get("text", "")

        if thinking_content:
            return f"<thinking>\n{thinking_content}\n</thinking>\n\n{text_content}"
        return text_content

    def messages_url(self) -> str:
        return f"{self.config.base_url.rstrip('/')}/v1/messages"

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
        }
