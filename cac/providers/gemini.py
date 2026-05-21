"""Google Gemini provider Adapter."""

from __future__ import annotations

from typing import Any, cast

import requests

from .base import ToolCapableProvider


class GeminiProvider(ToolCapableProvider):
    def chat_with_tool(self, prompt: str, tool_schema: dict[str, Any]) -> dict[str, Any]:
        gemini_func = {
            "name": tool_schema["name"],
            "description": tool_schema.get("description", ""),
            "parameters": tool_schema["parameters"],
        }
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"functionDeclarations": [gemini_func]}],
            "toolConfig": {
                "functionCallingConfig": {
                    "mode": "ANY",
                    "allowedFunctionNames": [tool_schema["name"]],
                }
            },
            "generationConfig": {
                "temperature": self.get_param("temperature"),
                "maxOutputTokens": self.get_param("max_tokens"),
            },
        }
        response = requests.post(
            self.generate_url(),
            headers={"Content-Type": "application/json"},
            json=data,
            params={"key": self.config.api_key},
            timeout=self.get_param("timeout"),
        )
        response.raise_for_status()
        result = response.json()
        parts = result["candidates"][0]["content"]["parts"]
        for part in parts:
            if "functionCall" in part:
                return cast(dict[str, Any], part["functionCall"]["args"])
        raise ValueError("Gemini 响应中未找到 functionCall")

    def chat(self, prompt: str) -> str:
        generation_config: dict[str, Any] = {
            "temperature": self.get_param("temperature"),
            "maxOutputTokens": self.get_param("max_tokens"),
        }
        if "top_p" in self.config.params:
            generation_config["topP"] = self.config.params["top_p"]
        if "top_k" in self.config.params:
            generation_config["topK"] = self.config.params["top_k"]

        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": generation_config,
        }
        response = requests.post(
            self.generate_url(),
            headers={"Content-Type": "application/json"},
            json=data,
            params={"key": self.config.api_key},
            timeout=self.get_param("timeout"),
        )
        response.raise_for_status()
        result = response.json()
        return cast(str, result["candidates"][0]["content"]["parts"][0]["text"])

    def generate_url(self) -> str:
        return f"{self.config.base_url.rstrip('/')}/v1beta/models/{self.config.model_id}:generateContent"
