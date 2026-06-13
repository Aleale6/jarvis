"""Safety, risk assessment, and the permission/confirmation pipeline.

The master spec requires that every action that can affect the system or data
pass through a verification pipeline: understand -> plan -> assess risk -> check
permission -> confirm (when impactful) -> execute -> verify -> log.

This module owns the *risk assessment*, *permission check*, and *confirmation*
stages. Skills describe the action they want to perform as a
:class:`SafetyRequest`; the :class:`SafetyManager` returns a
:class:`SafetyVerdict` telling the caller whether to proceed, deny, or ask the
user for confirmation first. The manager logs every decision through the
structured :class:`~jarvis.core.logging_setup.EventLogger`.

The design keeps policy (what is allowed / what needs confirming) separate from
mechanism (how a skill performs the action), so new skills inherit consistent,
auditable safety behaviour for free.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

from .logging_setup import EventLogger, get_event_logger


class RiskLevel(enum.IntEnum):
    """How impactful an action is. Higher means more caution required."""

    LOW = 0      # read-only or trivially reversible (tell time, search web)
    MEDIUM = 1   # changes state but is recoverable (open/close app, set volume)
    HIGH = 2     # hard to reverse or sensitive (delete files, run shell, shutdown)


class Decision(enum.Enum):
    """Outcome of evaluating a :class:`SafetyRequest`."""

    ALLOW = "allow"                # proceed immediately
    CONFIRM = "confirm"            # ask the user, then proceed if they agree
    DENY = "deny"                  # blocked by policy; do not proceed


# Permission categories a user can pre-authorize. Categories map many concrete
# actions to one toggle, so users reason about classes of capability, not every
# individual command.
PERMISSION_CATEGORIES = (
    "app_control",      # launching / closing applications
    "system_settings",  # volume, screen lock, display, power
    "file_read",        # reading files and folders
    "file_write",       # creating / renaming / moving / deleting files
    "shell",            # running PowerShell / cmd / arbitrary commands
    "web",              # opening URLs / web searches
    "network",          # other outbound network actions
)


@dataclass
class SafetyRequest:
    """A description of an action a skill (or agent) wants to perform.

    Attributes
    ----------
    agent:
        The component requesting the action (for the audit log).
    action:
        Short verb phrase, e.g. ``"open notepad"`` or ``"delete file"``.
    category:
        One of :data:`PERMISSION_CATEGORIES`.
    risk:
        The assessed :class:`RiskLevel`.
    description:
        A localized, user-facing phrase describing the effect, used in the
        confirmation prompt (e.g. ``"open notepad"`` -> "This will open notepad").
    reversible:
        Whether the action can be easily undone. Irreversible actions are never
        auto-approved even when their category is pre-authorized.
    detail:
        Structured context for the audit log (no secrets).
    """

    agent: str
    action: str
    category: str
    risk: RiskLevel = RiskLevel.LOW
    description: str = ""
    reversible: bool = True
    detail: Dict[str, object] = field(default_factory=dict)


@dataclass
class SafetyVerdict:
    """The manager's ruling on a :class:`SafetyRequest`."""

    decision: Decision
    request: SafetyRequest
    reason: str = ""

    @property
    def allowed(self) -> bool:
        return self.decision is Decision.ALLOW

    @property
    def needs_confirmation(self) -> bool:
        return self.decision is Decision.CONFIRM

    @property
    def denied(self) -> bool:
        return self.decision is Decision.DENY


#: A confirmation callback returns True if the user approved the action.
ConfirmCallback = Callable[[SafetyRequest], bool]


class SafetyManager:
    """Evaluates requests against policy and orchestrates confirmation.

    Policy inputs
    -------------
    granted:
        Categories the user has pre-authorized (no confirmation needed for
        LOW/MEDIUM, reversible actions in these categories).
    blocked:
        Categories that are always denied.
    confirm_medium:
        When True (default), MEDIUM-risk actions require confirmation unless
        their category is pre-authorized. When False, only HIGH risk requires it.
    auto_confirm:
        Test/automation escape hatch. When True, the manager treats a needed
        confirmation as automatically granted (still logged as ``confirmed``).

    The manager is constructed from config via :meth:`from_config`.
    """

    def __init__(
        self,
        granted: Optional[set[str]] = None,
        blocked: Optional[set[str]] = None,
        confirm_medium: bool = True,
        auto_confirm: bool = False,
        logger: Optional[EventLogger] = None,
    ):
        self.granted = set(granted or set())
        self.blocked = set(blocked or set())
        self.confirm_medium = confirm_medium
        self.auto_confirm = auto_confirm
        self._logger = logger or get_event_logger()

    @classmethod
    def from_config(
        cls, safety_cfg: Optional[Dict[str, object]], logger: Optional[EventLogger] = None
    ) -> "SafetyManager":
        cfg = safety_cfg or {}
        granted = {str(c).lower() for c in cfg.get("granted_permissions", []) or []}
        blocked = {str(c).lower() for c in cfg.get("blocked_permissions", []) or []}
        return cls(
            granted=granted,
            blocked=blocked,
            confirm_medium=bool(cfg.get("confirm_medium_risk", True)),
            auto_confirm=bool(cfg.get("auto_confirm", False)),
            logger=logger,
        )

    # -- evaluation -----------------------------------------------------
    def evaluate(self, request: SafetyRequest) -> SafetyVerdict:
        """Assess a request and return a verdict (without executing anything)."""
        verdict = self._decide(request)
        self._logger.log(
            agent="safety",
            action=request.action,
            result=verdict.decision.value,
            level="info" if verdict.decision is not Decision.DENY else "warning",
            category=request.category,
            risk=request.risk.name,
            reversible=request.reversible,
            reason=verdict.reason,
            **request.detail,
        )
        return verdict

    def _decide(self, request: SafetyRequest) -> SafetyVerdict:
        category = request.category.lower()

        # 1) Hard block always wins.
        if category in self.blocked:
            return SafetyVerdict(Decision.DENY, request, reason="category_blocked")

        # 2) Low risk, reversible: allow.
        if request.risk <= RiskLevel.LOW and request.reversible:
            return SafetyVerdict(Decision.ALLOW, request, reason="low_risk")

        # 3) High risk OR irreversible: always confirm (never silently auto-run).
        if request.risk >= RiskLevel.HIGH or not request.reversible:
            return SafetyVerdict(Decision.CONFIRM, request, reason="high_or_irreversible")

        # 4) Medium risk: pre-authorized category skips confirmation.
        if category in self.granted:
            return SafetyVerdict(Decision.ALLOW, request, reason="pre_authorized")
        if self.confirm_medium:
            return SafetyVerdict(Decision.CONFIRM, request, reason="medium_risk")
        return SafetyVerdict(Decision.ALLOW, request, reason="medium_risk_auto")

    # -- full gate (evaluate + confirm) ---------------------------------
    def gate(
        self, request: SafetyRequest, confirm: Optional[ConfirmCallback] = None
    ) -> Decision:
        """Run the full gate and return the *final* decision.

        Unlike :meth:`evaluate` (which only assesses), ``gate`` resolves a
        CONFIRM verdict by invoking the ``confirm`` callback and returns one of:
          * :attr:`Decision.ALLOW`  - proceed (low risk, pre-authorized, or the
            user approved the confirmation).
          * :attr:`Decision.DENY`   - blocked by policy.
          * :attr:`Decision.CONFIRM`- the action needed confirmation and the user
            declined (or none could be obtained). Treat as "do not proceed", but
            distinct from a policy DENY so callers can phrase the reply correctly.

        Confirmation resolution:
          * ``auto_confirm=True`` -> approved (logged as confirmed).
          * no callback           -> declined (safe default).
        """
        verdict = self.evaluate(request)
        if verdict.allowed:
            return Decision.ALLOW
        if verdict.denied:
            return Decision.DENY

        # CONFIRM path - ask the user.
        if self.auto_confirm:
            approved = True
        elif confirm is None:
            approved = False
        else:
            approved = bool(confirm(request))

        self._logger.log(
            agent="safety",
            action=request.action,
            result="confirmed" if approved else "cancelled",
            level="info",
            confirmed=approved,
            category=request.category,
            risk=request.risk.name,
        )
        return Decision.ALLOW if approved else Decision.CONFIRM

    def authorize(
        self, request: SafetyRequest, confirm: Optional[ConfirmCallback] = None
    ) -> bool:
        """Convenience wrapper over :meth:`gate` returning a simple boolean.

        Returns True only when the action may proceed.
        """
        return self.gate(request, confirm=confirm) is Decision.ALLOW
