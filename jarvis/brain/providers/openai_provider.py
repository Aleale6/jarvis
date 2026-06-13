"""OpenAI-compatible chat provider.

Works with the OpenAI ``/chat/completions`` schema, which is also implemented by
Azure OpenAI gateways and local servers such as Ollama and LM Studio when run in
OpenAI-compatible mode. The same class therefore backs both the cloud "openai"
provider and a "local" provider - the only differences are the base URL and the
``local`` capability flag (set via config).
"""

from __future__ import annotations

from typing import List, Optional

from .base import BaseProvider, Message, ProviderError


class OpenAIProvider(BaseProvider):
    kind = "openai"

    def _complete(
        self,
        messages: List[Message],
        *,
        system: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        url = f"{self.base_url or 'https://api.openai.com/v1'}/chat/completions"

        full_messages: List[Message] = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": full_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        data = self._post_json(url, payload, headers, self.timeout)
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"Unexpected OpenAI response shape: {exc}") from exc
