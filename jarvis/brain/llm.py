"""LLM brain: answers open-ended questions via an OpenAI-compatible chat API.

Works with any endpoint that implements the OpenAI ``/chat/completions`` schema
(OpenAI, Azure OpenAI gateways, local servers like Ollama/LM Studio in OpenAI
mode, etc.). Keeps a short rolling conversation history for context.

If no API key is configured, ``enabled`` is False and the assistant simply tells
the user that conversational answers require a key — the built-in skills keep
working regardless.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

# Inline fallback used only if neither a prompt file nor a configured
# ``system_prompt`` string is available.
_FALLBACK_SYSTEM_PROMPT = "You are JARVIS, a concise voice assistant."


class LLMBrain:
    def __init__(self, llm_cfg: Optional[Dict[str, Any]] = None):
        cfg = llm_cfg or {}
        self.base_url = str(cfg.get("base_url", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = cfg.get("api_key", "") or ""
        self.model = cfg.get("model", "gpt-4o-mini")
        self.system_prompt = self._load_system_prompt(cfg)
        self.max_history = int(cfg.get("max_history", 12))
        self.temperature = float(cfg.get("temperature", 0.6))
        self.timeout = int(cfg.get("timeout_seconds", 30))

        self._configured_enabled = bool(cfg.get("enabled", True))
        self._history: List[Dict[str, str]] = []

    @staticmethod
    def _load_system_prompt(cfg: Dict[str, Any]) -> str:
        """Resolve the system prompt.

        Order of precedence:
            1. The file named by ``system_prompt_file`` (or the bundled
               ``system_prompt.md`` next to this module if not set).
            2. The inline ``system_prompt`` string from config.
            3. A short built-in fallback.

        A relative ``system_prompt_file`` is resolved against the project root
        (the folder that contains the ``jarvis`` package).
        """
        inline = cfg.get("system_prompt")
        configured = cfg.get("system_prompt_file")

        module_dir = Path(__file__).resolve().parent          # jarvis/brain
        project_root = module_dir.parent.parent               # repo root

        if configured:
            prompt_path = Path(configured)
            if not prompt_path.is_absolute():
                prompt_path = project_root / prompt_path
        else:
            prompt_path = module_dir / "system_prompt.md"

        try:
            text = prompt_path.read_text(encoding="utf-8").strip()
            if text:
                return text
        except OSError:
            # File missing or unreadable: fall through to the inline string.
            if configured:
                print(f"[brain] Could not read system prompt file '{prompt_path}'. Using inline prompt.")

        if inline:
            return str(inline)
        return _FALLBACK_SYSTEM_PROMPT

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
