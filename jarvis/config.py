"""Configuration loading for JARVIS.

Loads settings from ``config.json`` (falling back to ``config.example.json``)
and overlays environment variables so secrets like the API key never need to
live in the file.

Environment overrides:
    JARVIS_API_KEY   -> llm.api_key
    JARVIS_MODEL     -> llm.model
    JARVIS_BASE_URL  -> llm.base_url
    JARVIS_WAKE_WORD -> wake_word
    JARVIS_LANGUAGE  -> language  (en | ru | de | ar)
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any, Dict

# Sensible built-in defaults so JARVIS can run even without a config file.
DEFAULTS: Dict[str, Any] = {
    "assistant_name": "Jarvis",
    "wake_word": "jarvis",
    "language": "en",
    "auto_detect_language": True,
    "voice": {"rate": 175, "volume": 1.0, "voice_index": 0},
    "listener": {
        "energy_threshold": 300,
        "dynamic_energy": True,
        "pause_threshold": 0.8,
        "phrase_time_limit": 8,
        "language": "en-US",
    },
    "safety": {
        "granted_permissions": [],
        "blocked_permissions": [],
        "confirm_medium_risk": True,
        "auto_confirm": False,
    },
    "logging": {
        "file": "jarvis_events.log",
        "echo_console": True,
    },
    "llm": {
        "enabled": True,
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
        "model": "gpt-4o-mini",
        "private": False,
        "providers": [],
        "system_prompt_file": "jarvis/brain/system_prompt.md",
        "system_prompt": (
            "You are JARVIS, a concise, helpful voice assistant. "
            "Keep spoken replies short (1-3 sentences) unless asked for detail."
        ),
        "max_history": 12,
        "temperature": 0.6,
        "timeout_seconds": 30,
    },
    "exit_phrases": ["goodbye", "shut down", "power down", "exit", "quit"],
    "notes_file": "jarvis_notes.txt",
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge ``override`` into a copy of ``base``."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class Config:
    """Dot/section accessor over the merged configuration dictionary."""

    def __init__(self, data: Dict[str, Any]):
        self._data = data

    # -- access helpers -------------------------------------------------
    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def section(self, name: str) -> Dict[str, Any]:
        """Return a config sub-section as a plain dict (never None)."""
        value = self._data.get(name, {})
        return value if isinstance(value, dict) else {}

    @property
    def data(self) -> Dict[str, Any]:
        return self._data

    # -- loading --------------------------------------------------------
    @classmethod
    def load(cls, base_dir: Path | str | None = None) -> "Config":
        base_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent

        config_path = base_dir / "config.json"
        example_path = base_dir / "config.example.json"

        file_data: Dict[str, Any] = {}
        chosen = config_path if config_path.exists() else example_path
        if chosen.exists():
            try:
                with open(chosen, "r", encoding="utf-8") as fh:
                    file_data = json.load(fh)
            except (json.JSONDecodeError, OSError) as exc:
                print(f"[config] Could not read {chosen.name}: {exc}. Using defaults.")
                file_data = {}

        merged = _deep_merge(DEFAULTS, file_data)
        merged = cls._apply_env_overrides(merged)
        return cls(merged)

    @staticmethod
    def _apply_env_overrides(data: Dict[str, Any]) -> Dict[str, Any]:
        llm = data.setdefault("llm", {})
        api_key = os.environ.get("JARVIS_API_KEY")
        model = os.environ.get("JARVIS_MODEL")
        base_url = os.environ.get("JARVIS_BASE_URL")

        # Always set the flat keys so the legacy single-provider path works.
        if api_key:
            llm["api_key"] = api_key
        if model:
            llm["model"] = model
        if base_url:
            llm["base_url"] = base_url

        # When a providers list is configured, route the env secret to the first
        # OpenAI-compatible provider (or the first provider) so users can supply a
        # key via environment without editing config.json.
        providers = llm.get("providers") or []
        if providers and (api_key or model or base_url):
            target = next(
                (p for p in providers if str(p.get("type", "")).lower() in ("openai", "local")),
                providers[0],
            )
            if api_key:
                target["api_key"] = api_key
            if model:
                target["model"] = model
            if base_url:
                target["base_url"] = base_url

        wake = os.environ.get("JARVIS_WAKE_WORD")
        if wake:
            data["wake_word"] = wake

        language = os.environ.get("JARVIS_LANGUAGE")
        if language:
            data["language"] = language

        return data
