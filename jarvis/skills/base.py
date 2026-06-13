"""Skill framework.

A *skill* is a small handler that can claim a spoken command and act on it.
Each skill implements:
    * ``matches(text)`` -> bool : does this skill want to handle the command?
    * ``run(text, ctx)`` -> str : perform the action and return a spoken reply.

The ``SkillContext`` gives skills access to shared services (the speaker and
config) without tight coupling to the Assistant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, List

from ..core.safety import SafetyRequest

if TYPE_CHECKING:  # avoid runtime import cycles
    from ..config import Config
    from ..core.logging_setup import EventLogger
    from ..core.safety import SafetyManager
    from ..i18n import Localizer
    from ..speech.speaker import Speaker


def _default_confirm(_request: "SafetyRequest") -> bool:
    """Fallback confirm callback: declines (safe default) when none is wired."""
    return False


@dataclass
class SkillContext:
    """Shared services handed to every skill.

    Skills translate their replies via :attr:`localizer`, gate any
    system-affecting action through :attr:`safety` (using :attr:`confirm` to ask
    the user), and record outcomes via :attr:`logger` - so safety, i18n, and
    auditing are consistent across all skills without each reimplementing them.
    """

    config: "Config"
    speaker: "Speaker"
    localizer: "Localizer"
    safety: "SafetyManager"
    logger: "EventLogger"
    confirm: Callable[["SafetyRequest"], bool] = field(default=_default_confirm)

    def t(self, key: str, **kwargs: object) -> str:
        """Shorthand for ``self.localizer.t(key, **kwargs)``."""
        return self.localizer.t(key, **kwargs)


class Skill:
    """Base class for all skills."""

    #: Human-friendly name, shown in help.
    name: str = "skill"
    #: Short description of what the skill does.
    description: str = ""

    def matches(self, text: str) -> bool:
        raise NotImplementedError

    def run(self, text: str, ctx: SkillContext) -> str:
        raise NotImplementedError

    @staticmethod
    def _contains_any(text: str, keywords: List[str]) -> bool:
        return any(kw in text for kw in keywords)


def default_skills() -> List[Skill]:
    """Instantiate the built-in skills in priority order (first match wins)."""
    # Imported here to avoid circular imports at module load time.
    from .time_date import TimeDateSkill
    from .notes import NotesSkill
    from .web import WebSkill
    from .system_control import SystemControlSkill

    return [
        TimeDateSkill(),
        NotesSkill(),
        WebSkill(),
        SystemControlSkill(),
    ]
