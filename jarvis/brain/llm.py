"""LLM brain: answers open-ended questions through the multi-provider router.

This module keeps the small, stable surface the rest of JARVIS relies on
(``LLMBrain.enabled`` and ``LLMBrain.ask(prompt)``) while delegating the actual
model call to :class:`~jarvis.brain.router.ProviderRouter`. That router picks an
appropriate backend (OpenAI / Anthropic / Gemini / local) based on task type,
privacy, language, and availability, and falls back on failure.

Two cross-cutting concerns are handled here:
  * **Language steering** - a per-language directive is appended to the system
    prompt so the model replies in the user's chosen language (en/ru/de/ar),
    matching the spoken output of the TTS voice.
  * **Conversation memory** - a short rolling window of turns for context.

Backward compatibility: a flat legacy ``llm`` config (single base_url/api_key/
model) still works; the router synthesizes a provider from it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ..i18n import Localizer
from .router import ProviderRouter, RouteRequirements, TaskType

_FALLBACK_SYSTEM_PROMPT = "You are JARVIS, a concise voice assistant."

# Lightweight keyword cues to bias task routing. Not exhaustive - just enough to
# send obviously code-related questions to a coding-strong provider.
_CODING_CUES = (
    "code", "function", "bug", "error", "stack trace", "compile", "python",
    "javascript", "typescript", "regex", "sql", "api", "exception", "debug",
)
_REASONING_CUES = (
    "why", "explain", "plan", "compare", "analyze", "analyse", "reason",
    "strategy", "trade-off", "tradeoff", "design",
)


class LLMBrain:
    def __init__(
        self,
        llm_cfg: Optional[Dict[str, Any]] = None,
        localizer: Optional[Localizer] = None,
    ):
        cfg = llm_cfg or {}
        self._base_system_prompt = self._load_system_prompt(cfg)
        self.max_history = int(cfg.get("max_history", 12))
        self.temperature = float(cfg.get("temperature", 0.6))
        self.private = bool(cfg.get("private", False))

        self._configured_enabled = bool(cfg.get("enabled", True))
        self._localizer = localizer or Localizer()
        self._router = ProviderRouter.from_config(cfg)
        self._history: List[Dict[str, str]] = []

    @staticmethod
    def _load_system_prompt(cfg: Dict[str, Any]) -> str:
        """Resolve the base system prompt (file -> inline string -> fallback)."""
        inline = cfg.get("system_prompt")
        configured = cfg.get("system_prompt_file")

        module_dir = Path(__file__).resolve().parent       # jarvis/brain
        project_root = module_dir.parent.parent            # repo root

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
            if configured:
                print(f"[brain] Could not read system prompt file '{prompt_path}'. Using inline prompt.")

        if inline:
            return str(inline)
        return _FALLBACK_SYSTEM_PROMPT

    # -- language -------------------------------------------------------
    def set_language(self, language: str) -> None:
        """Switch the language the model is instructed to reply in."""
        self._localizer = self._localizer.with_language(language)

    @property
    def _system_prompt(self) -> str:
        """Base prompt plus the active-language directive."""
        directive = self._localizer.t("llm.language_directive")
        return f"{self._base_system_prompt}\n\n{directive}"

    @property
    def enabled(self) -> bool:
        """True only if conversation is on AND at least one provider is usable."""
        return self._configured_enabled and self._router.has_available_provider

    def reset(self) -> None:
        self._history.clear()

    # -- task classification -------------------------------------------
    @staticmethod
    def _classify(prompt: str) -> TaskType:
        low = prompt.lower()
        if any(cue in low for cue in _CODING_CUES):
            return TaskType.CODING
        if any(cue in low for cue in _REASONING_CUES):
            return TaskType.REASONING
        return TaskType.CHAT

    # -- main entry point ----------------------------------------------
    def ask(self, prompt: str) -> Optional[str]:
        """Send ``prompt`` (with history) to the router; return the reply or None."""
        if not self.enabled:
            return None

        messages = list(self._history)
        messages.append({"role": "user", "content": prompt})

        requirements = RouteRequirements(
            task=self._classify(prompt),
            private=self.private,
            language=self._localizer.language,
        )

        result = self._router.complete(
            messages,
            system=self._system_prompt,
            requirements=requirements,
            temperature=self.temperature,
        )
        if result is None:
            return None

        self._remember(prompt, result.text)
        return result.text

    def _remember(self, user_text: str, assistant_text: str) -> None:
        self._history.append({"role": "user", "content": user_text})
        self._history.append({"role": "assistant", "content": assistant_text})
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history :]
