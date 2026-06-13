"""Google Gemini chat provider using the ``generateContent`` REST endpoint.

Gemini's schema uses ``contents`` with ``role`` (``user`` / ``model``) and
``parts``. There is no dedicated assistant role name - the model's turns use
``model`` - and the system prompt is passed as ``systemInstruction``. The API
key is supplied as a query parameter.
"""

from __future__ import annotations

from typing import List, Optional

from .base import BaseProvider, Message, ProviderError


class GeminiProvider(BaseProvider):
    kind = "gemini"

    def _complete(
        self,
        messages: List[Message],
        *,
        system: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        base = self.base_url or "https://generativelanguage.googleapis.com/v1beta"
        url = f"{base}/models/{self.model}:generateContent?key={self.api_key}"

        contents = []
        for msg in messages:
            role = msg.get("role")
            if role not in ("user", "assistant"):
                continue
            gemini_role = "model" if role == "assistant" else "user"
            contents.append({"role": gemini_role, "parts": [{"text": msg.get("content", "")}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        headers = {"Content-Type": "application/json"}
        data = self._post_json(url, payload, headers, self.timeout)
        try:
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(part.get("text", "") for part in parts)
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"Unexpected Gemini response shape: {exc}") from exc
