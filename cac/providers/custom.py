"""Custom OpenAI-compatible endpoint Adapter."""

from __future__ import annotations

from .openai import OpenAIProvider


class CustomProvider(OpenAIProvider):
    def chat_url(self) -> str:
        return self.config.base_url
