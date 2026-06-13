"""LLM brain: answers open-ended questions via an OpenAI-compatible chat API.

Works with any endpoint that implements the OpenAI ``/chat/completions`` schema
(OpenAI, Azure OpenAI gateways, local servers like Ollama/LM Studio in OpenAI
mode, etc.). Keeps a short rolling conversation history for context.

If no API key is configured, ``enabled`` is False and the assistant simply tells
the user that conversational answers require a key — the built-in skills keep
working regardless.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class LLMBrain:
    def __init__(self, llm_cfg: Optional[Dict[str, Any]] = None):
        cfg = llm_cfg or {}
        self.base_url = str(cfg.get("base_url", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = cfg.get("api_key", "") or ""
        self.model = cfg.get("model", "gpt-4o-mini")
        self.system_prompt = cfg.get("system_prompt", "You are JARVIS, a concise voice assistant.")
        self.max_history = int(cfg.get("max_history", 12))
        self.temperature = float(cfg.get("temperature", 0.6))
        self.timeout = int(cfg.get("timeout_seconds", 30))

        self._configured_enabled = bool(cfg.get("enabled", True))
        self._history: List[Dict[str, str]] = []

    @property
    def enabled(self) -> bool:
        """True only if conversation is turned on AND we have an API key."""
        return self._configured_enabled and bool(self.api_key)

    def reset(self) -> None:
        self._history.clear()

    def ask(self, prompt: str) -> Optional[str]:
        """Send ``prompt`` to the LLM with history; return the reply text or None."""
        if not self.enabled:
            return None

        try:
            import requests
        except ImportError:
            print("[brain] 'requests' is not installed; cannot reach the LLM.")
            return None

        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self._history)
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            reply = data["choices"][0]["message"]["content"].strip()
        except requests.exceptions.Timeout:
            return "Sorry, the request timed out."
        except requests.exceptions.RequestException as exc:
            print(f"[brain] LLM request failed: {exc}")
            return "Sorry, I couldn't reach my reasoning service."
        except (KeyError, IndexError, ValueError) as exc:
            print(f"[brain] Unexpected LLM response: {exc}")
            return "Sorry, I got an unexpected response."

        self._remember(prompt, reply)
        return reply

    def _remember(self, user_text: str, assistant_text: str) -> None:
        self._history.append({"role": "user", "content": user_text})
        self._history.append({"role": "assistant", "content": assistant_text})
        # keep only the most recent N messages (pairs)
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history :]
