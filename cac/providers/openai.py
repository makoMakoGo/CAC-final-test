"""OpenAI-compatible provider Adapters."""

from __future__ import annotations

import json
import sys
import time
from typing import Any, cast

import requests

from .base import ToolCapableProvider


class OpenAIProvider(ToolCapableProvider):
    def chat_with_tool(self, prompt: str, tool_schema: dict[str, Any]) -> dict[str, Any]:
        headers = self._headers()
        data = {
            "model": self.config.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "tools": [{"type": "function", "function": tool_schema}],
            "tool_choice": {"type": "function", "function": {"name": tool_schema["name"]}},
            "temperature": self.get_param("temperature"),
            "max_tokens": self.get_param("max_tokens"),
        }
        response = requests.post(
            self.chat_url(), headers=headers, json=data, timeout=self.get_param("timeout")
        )
        response.raise_for_status()
        result = response.json()
        tool_call = result["choices"][0]["message"]["tool_calls"][0]
        return cast(dict[str, Any], json.loads(tool_call["function"]["arguments"]))

    def chat(self, prompt: str) -> str:
        stream = bool(self.config.params.get("stream", False))
        data = {
            "model": self.config.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream,
            **self.config.params,
        }
        url = self.chat_url()
        timeout = self.get_param("timeout")
        if stream:
            return self._stream_chat(url, self._headers(), data, timeout)

        response = requests.post(url, headers=self._headers(), json=data, timeout=timeout)
        response.raise_for_status()
        return cast(str, response.json()["choices"][0]["message"]["content"])

    def chat_url(self) -> str:
        base_url = self.config.base_url.rstrip("/")
        return (
            base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

    def _stream_chat(
        self,
        url: str,
        headers: dict[str, str],
        data: dict[str, Any],
        timeout: int,
    ) -> str:
        start = time.time()
        ttft = None
        chunks = 0
        content = []
        is_tty = sys.stderr.isatty()

        with requests.post(url, headers=headers, json=data, timeout=timeout, stream=True) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                decoded = line.decode("utf-8")
                if not decoded.startswith("data: "):
                    continue
                payload = decoded[6:]
                if payload == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                text = delta.get("content", "")
                if text:
                    if ttft is None:
                        ttft = time.time() - start
                    chunks += 1
                    content.append(text)
                    if is_tty:
                        elapsed = time.time() - start
                        sys.stderr.write(
                            f"\r  ⏳ TTFT: {ttft:.2f}s | {elapsed:.1f}s | ~{chunks} chunks"
                        )
                        sys.stderr.flush()

        if is_tty:
            sys.stderr.write("\r" + " " * 60 + "\r")
            sys.stderr.flush()
        return "".join(content)
