"""Skill framework.

A *skill* is a small handler that can claim a spoken command and act on it.
Each skill implements:
    * ``matches(text)`` -> bool : does this skill want to handle the command?
    * ``run(text, ctx)`` -> str : perform the action and return a spoken reply.

The ``SkillContext`` gives skills access to shared services (the speaker and
config) without tight coupling to the Assistant.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, List

if TYPE_CHECKING:  # avoid runtime import cycles
    from ..config import Config
    from ..speech.speaker import Speaker


@dataclass
class SkillContext:
    config: "Config"
    speaker: "Speaker"


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
