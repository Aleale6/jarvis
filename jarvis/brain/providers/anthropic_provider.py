"""Anthropic (Claude) chat provider using the Messages API.

The Messages API differs from OpenAI's schema in two ways this provider handles:
  * The system prompt is a top-level ``system`` field, not a message.
  * The response content is a list of typed blocks; we concatenate the text ones.
"""

from __future__ import annotations

from typing import List, Optional

from .base import BaseProvider, Message, ProviderError

#: Pinned API version header required by the Anthropic Messages API.
_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(BaseProvider):
    kind = "anthropic"

    def _complete(
        self,
        messages: List[Message],
        *,
        system: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        url = f"{self.base_url or 'https://api.anthropic.com/v1'}/messages"

        # Anthropic requires alternating user/assistant roles and rejects a
        # 'system' role inside messages, so we only forward user/assistant turns.
        convo = [m for m in messages if m.get("role") in ("user", "assistant")]

        payload = {
            "model": self.model,
            "messages": convo,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            payload["system"] = system

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
        }

        data = self._post_json(url, payload, headers, self.timeout)
        try:
            blocks = data["content"]
            text = "".join(
                block.get("text", "")
                for block in blocks
                if block.get("type") == "text"
            )
        except (KeyError, TypeError) as exc:
            raise ProviderError(f"Unexpected Anthropic response shape: {exc}") from exc
        return text
