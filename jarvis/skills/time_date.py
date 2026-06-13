"""Tells the current time and date (multilingual triggers)."""

from __future__ import annotations

from datetime import datetime

from ..i18n.triggers import matches_any
from .base import Skill, SkillContext


class TimeDateSkill(Skill):
    name = "time_date"
    description = "Tell the current time or today's date."

    def matches(self, text: str) -> bool:
        return matches_any(text, "time.time") or matches_any(text, "time.date")

    def run(self, text: str, ctx: SkillContext) -> str:
        now = datetime.now()
        # Date check first: a date phrase is more specific than a bare "time".
        if matches_any(text, "time.date"):
            return ctx.t("skill.time.today", date=now.strftime("%A, %B %d, %Y"))
        return ctx.t("skill.time.now", time=now.strftime("%I:%M %p").lstrip("0"))
