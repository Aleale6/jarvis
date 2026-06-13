"""Chat providers and a small factory keyed by provider ``kind``.

Adding a new backend is a two-step process: implement a ``BaseProvider``
subclass and register it in :data:`PROVIDER_TYPES` (or, in future, via a plugin
that calls :func:`register_provider`).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Type

from .anthropic_provider import AnthropicProvider
from .base import (
    BaseProvider,
    Capabilities,
    CompletionResult,
    Message,
    ProviderError,
)
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider

#: provider ``kind`` -> implementing class. "local" reuses the OpenAI schema.
PROVIDER_TYPES: Dict[str, Type[BaseProvider]] = {
    "openai": OpenAIProvider,
    "local": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
}


def register_provider(kind: str, cls: Type[BaseProvider]) -> None:
    """Register a provider class under ``kind`` (used by plugins)."""
    PROVIDER_TYPES[kind.lower()] = cls


def build_provider(cfg: Dict[str, Any]) -> Optional[BaseProvider]:
    """Construct a provider from a config dict, or return None if unknown/off.

    Expected config keys::

        {
          "type": "openai" | "local" | "anthropic" | "gemini",
          "name": "openai-main",          # optional, defaults to type
          "model": "gpt-4o-mini",
          "api_key": "...",                # optional for local
          "base_url": "...",               # optional
          "enabled": true,                 # optional, default true
          "priority": 10,                  # optional, lower = preferred
          "timeout_seconds": 30,           # optional
          "capabilities": {                # optional overrides
              "reasoning": 4, "coding": 4, "context_tokens": 128000,
              "vision": false, "local": false,
              "languages": ["en", "ru", "de", "ar"]
          }
        }
    """
    if not cfg or not cfg.get("enabled", True):
        return None

    kind = str(cfg.get("type", "")).lower()
    cls = PROVIDER_TYPES.get(kind)
    if cls is None:
        return None

    cap_cfg = cfg.get("capabilities", {}) or {}
    languages = cap_cfg.get("languages")
    capabilities = Capabilities(
        reasoning=int(cap_cfg.get("reasoning", 3)),
        coding=int(cap_cfg.get("coding", 3)),
        context_tokens=int(cap_cfg.get("context_tokens", 8000)),
        vision=bool(cap_cfg.get("vision", False)),
        local=bool(cap_cfg.get("local", kind == "local")),
        languages=set(languages) if languages else {"en", "ru", "de", "ar"},
    )

    return cls(
        name=str(cfg.get("name", kind)),
        model=str(cfg.get("model", "")),
        api_key=str(cfg.get("api_key", "") or ""),
        base_url=str(cfg.get("base_url", "") or ""),
        capabilities=capabilities,
        timeout=int(cfg.get("timeout_seconds", 30)),
        priority=int(cfg.get("priority", 100)),
    )


__all__ = [
    "BaseProvider",
    "Capabilities",
    "CompletionResult",
    "Message",
    "ProviderError",
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "PROVIDER_TYPES",
    "register_provider",
    "build_provider",
]
