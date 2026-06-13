"""The AI provider router.

Given a list of configured providers, the router chooses the best candidate for
a request and falls through to the next on failure. Selection considers the
factors the master spec calls for: task type (reasoning vs coding vs chat),
privacy requirement (force a local model), language support, and availability.

The router is provider-agnostic: it only depends on the :class:`BaseProvider`
interface, so cloud and local backends - and future plugin providers - are
ranked by the same rules.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import List, Optional

from ..core.logging_setup import EventLogger, get_event_logger
from .providers import BaseProvider, CompletionResult, Message, ProviderError, build_provider


class TaskType(enum.Enum):
    """The kind of work a request represents, used to weight capabilities."""

    CHAT = "chat"
    REASONING = "reasoning"
    CODING = "coding"


@dataclass
class RouteRequirements:
    """Constraints/preferences for routing a single request."""

    task: TaskType = TaskType.CHAT
    private: bool = False        # if True, only local providers are eligible
    language: str = "en"
    min_context: int = 0         # require at least this much context window


class ProviderRouter:
    """Selects and invokes providers with capability-aware fallback."""

    def __init__(
        self,
        providers: List[BaseProvider],
        logger: Optional[EventLogger] = None,
    ):
        self.providers = providers
        self._logger = logger or get_event_logger()

    @classmethod
    def from_config(
        cls, llm_cfg: dict, logger: Optional[EventLogger] = None
    ) -> "ProviderRouter":
        """Build a router from the ``llm`` config section.

        Supports two shapes for backward compatibility:
          * New: ``llm.providers`` is a list of provider configs.
          * Legacy: a single OpenAI-compatible provider described by the flat
            ``llm`` keys (base_url/api_key/model). This keeps old config.json
            files working unchanged.
        """
        provider_cfgs = list(llm_cfg.get("providers") or [])

        if not provider_cfgs:
            # Legacy single-provider config -> synthesize one provider entry.
            provider_cfgs = [
                {
                    "type": "openai",
                    "name": "openai",
                    "model": llm_cfg.get("model", "gpt-4o-mini"),
                    "api_key": llm_cfg.get("api_key", ""),
                    "base_url": llm_cfg.get("base_url", "https://api.openai.com/v1"),
                    "timeout_seconds": llm_cfg.get("timeout_seconds", 30),
                    "priority": 10,
                }
            ]

        providers: List[BaseProvider] = []
        for cfg in provider_cfgs:
            provider = build_provider(cfg)
            if provider is not None:
                providers.append(provider)

        return cls(providers, logger=logger)

    @property
    def has_available_provider(self) -> bool:
        return any(p.available for p in self.providers)

    # -- selection ------------------------------------------------------
    def _score(self, provider: BaseProvider, req: RouteRequirements) -> Optional[int]:
        """Return a score for a provider (higher is better), or None if unfit.

        Hard filters (return None): unavailable, privacy requires local but
        provider is cloud, language unsupported, or insufficient context window.
        """
        cap = provider.capabilities
        if not provider.available:
            return None
        if req.private and not cap.local:
            return None
        if not cap.supports_language(req.language):
            return None
        if req.min_context and cap.context_tokens < req.min_context:
            return None

        if req.task is TaskType.CODING:
            score = cap.coding * 10 + cap.reasoning
        elif req.task is TaskType.REASONING:
            score = cap.reasoning * 10 + cap.coding
        else:  # CHAT - balance reasoning with a mild bias toward local privacy
            score = cap.reasoning * 6 + cap.coding * 4 + (5 if cap.local else 0)

        # Prefer lower configured priority on ties (subtract a small amount).
        return score * 1000 - provider.priority

    def candidates(self, req: RouteRequirements) -> List[BaseProvider]:
        """Return eligible providers, best first."""
        scored = []
        for provider in self.providers:
            score = self._score(provider, req)
            if score is not None:
                scored.append((score, provider))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [provider for _, provider in scored]

    # -- execution ------------------------------------------------------
    def complete(
        self,
        messages: List[Message],
        *,
        system: Optional[str] = None,
        requirements: Optional[RouteRequirements] = None,
        temperature: float = 0.6,
        max_tokens: int = 1024,
    ) -> Optional[CompletionResult]:
        """Try eligible providers in order; return the first success or None.

        Every attempt is logged. Returning None (rather than raising) lets the
        assistant respond gracefully when all providers fail.
        """
        req = requirements or RouteRequirements()
        ordered = self.candidates(req)

        if not ordered:
            self._logger.warning(
                agent="router",
                action="route",
                result="no_provider",
                task=req.task.value,
                private=req.private,
                language=req.language,
            )
            return None

        last_error: Optional[str] = None
        for provider in ordered:
            try:
                result = provider.complete(
                    messages,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                self._logger.info(
                    agent="router",
                    action="route",
                    result="ok",
                    provider=provider.name,
                    model=provider.model,
                    task=req.task.value,
                )
                return result
            except ProviderError as exc:
                last_error = str(exc)
                self._logger.warning(
                    agent="router",
                    action="route",
                    result="provider_failed",
                    provider=provider.name,
                    error=last_error,
                )
                continue  # fall through to the next candidate

        self._logger.error(
            agent="router",
            action="route",
            result="all_failed",
            error=last_error or "no provider produced a response",
        )
        return None
