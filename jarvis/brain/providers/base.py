"""Provider abstraction for the AI router.

A *provider* is a thin, uniform wrapper around one chat-completion backend
(OpenAI, Anthropic, Google Gemini, or a local OpenAI-compatible server). The
router talks only to this interface, so new providers can be added - including
via plugins - without touching the router or the rest of the assistant.

Each provider exposes:
    * ``name`` and ``model`` for logging and selection.
    * ``available`` so the router can skip unconfigured backends.
    * ``capabilities`` so the router can match a request to a suitable backend.
    * ``complete(messages, ...)`` to actually produce a reply.

Providers must never raise for *expected* failures (network, auth, bad
response). Instead they raise :class:`ProviderError`, which the router catches to
fall through to the next candidate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

#: A chat message in the provider-neutral format: {"role": ..., "content": ...}.
Message = Dict[str, str]


class ProviderError(Exception):
    """Raised when a provider cannot fulfil a request (network/auth/format).

    The router treats this as "try the next provider"; it is never fatal.
    """


@dataclass
class Capabilities:
    """Declarative description of what a provider is good for.

    The router scores providers against a request's requirements using these
    flags. They are intentionally coarse - the goal is sensible routing, not a
    precise benchmark.
    """

    reasoning: int = 3          # 1-5 subjective reasoning strength
    coding: int = 3             # 1-5 coding/debugging strength
    context_tokens: int = 8000  # approximate usable context window
    vision: bool = False        # accepts image inputs
    local: bool = False         # runs locally (privacy-preserving, offline)
    languages: Set[str] = field(default_factory=lambda: {"en", "ru", "de", "ar"})

    def supports_language(self, lang: str) -> bool:
        return lang in self.languages or not self.languages


@dataclass
class CompletionResult:
    """A successful completion plus metadata for logging/telemetry."""

    text: str
    provider: str
    model: str


class BaseProvider:
    """Common base for all chat providers.

    Subclasses implement :meth:`_complete` (the backend-specific call). The base
    class handles availability and presents the public :meth:`complete`.
    """

    #: Stable identifier used in config and logs (e.g. "openai", "anthropic").
    kind: str = "base"

    def __init__(
        self,
        name: str,
        model: str,
        api_key: str = "",
        base_url: str = "",
        capabilities: Optional[Capabilities] = None,
        timeout: int = 30,
        priority: int = 100,
    ):
        self.name = name
        self.model = model
        self.api_key = api_key or ""
        self.base_url = (base_url or "").rstrip("/")
        self.capabilities = capabilities or Capabilities()
        self.timeout = timeout
        self.priority = priority  # lower = preferred when scores tie

    @property
    def available(self) -> bool:
        """Whether this provider is usable. Local providers need no API key."""
        return self.capabilities.local or bool(self.api_key)

    def complete(
        self,
        messages: List[Message],
        *,
        system: Optional[str] = None,
        temperature: float = 0.6,
        max_tokens: int = 1024,
    ) -> CompletionResult:
        """Produce a completion, raising :class:`ProviderError` on failure."""
        if not self.available:
            raise ProviderError(f"Provider '{self.name}' is not configured.")
        text = self._complete(
            messages, system=system, temperature=temperature, max_tokens=max_tokens
        )
        if not text or not text.strip():
            raise ProviderError(f"Provider '{self.name}' returned an empty response.")
        return CompletionResult(text=text.strip(), provider=self.name, model=self.model)

    # Subclasses implement this.
    def _complete(
        self,
        messages: List[Message],
        *,
        system: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:  # pragma: no cover - abstract
        raise NotImplementedError

    # Shared HTTP helper -------------------------------------------------
    @staticmethod
    def _post_json(
        url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: int
    ) -> Dict[str, Any]:
        """POST JSON and return parsed JSON, normalising errors to ProviderError."""
        try:
            import requests
        except ImportError as exc:  # pragma: no cover - requests is a core dep
            raise ProviderError("The 'requests' package is not installed.") from exc

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout as exc:
            raise ProviderError("Request timed out.") from exc
        except requests.exceptions.RequestException as exc:
            raise ProviderError(f"HTTP error: {exc}") from exc
        except ValueError as exc:
            raise ProviderError("Response was not valid JSON.") from exc
