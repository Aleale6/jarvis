"""Configuration loading for JARVIS.

Loads settings from ``config.json`` (falling back to ``config.example.json``)
and overlays environment variables so secrets like the API key never need to
live in the file.

Environment overrides:
    JARVIS_API_KEY   -> llm.api_key
    JARVIS_MODEL     -> llm.model
    JARVIS_BASE_URL  -> llm.base_url
    JARVIS_WAKE_WORD -> wake_word
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
    "voice": {"rate": 175, "volume": 1.0, "voice_index": 0},
    "listener": {
        "energy_threshold": 300,
        "dynamic_energy": True,
        "pause_threshold": 0.8,
        "phrase_time_limit": 8,
        "language": "en-US",
    },
    "llm": {
        "enabled": True,
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
        "model": "gpt-4o-mini",
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
        api_key = os.environ.get("JARVIS_API_KEY")
        if api_key:
            data["llm"]["api_key"] = api_key

        model = os.environ.get("JARVIS_MODEL")
        if model:
            data["llm"]["model"] = model

        base_url = os.environ.get("JARVIS_BASE_URL")
        if base_url:
            data["llm"]["base_url"] = base_url

        wake = os.environ.get("JARVIS_WAKE_WORD")
        if wake:
            data["wake_word"] = wake

        return data
