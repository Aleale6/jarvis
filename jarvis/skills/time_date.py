"""Tells the current time and date."""

from __future__ import annotations

from datetime import datetime

from .base import Skill, SkillContext


class TimeDateSkill(Skill):
    name = "time_date"
    description = "Tell the current time or today's date."

    def matches(self, text: str) -> bool:
        if "time" in text and self._contains_any(text, ["what", "tell", "current"]):
            return True
        if self._contains_any(text, ["what day", "what's the date", "what is the date", "today's date", "what date"]):
            return True
        return False

    def run(self, text: str, ctx: SkillContext) -> str:
        now = datetime.now()
        if "time" in text:
            return f"It's {now.strftime('%I:%M %p').lstrip('0')}."
        return f"Today is {now.strftime('%A, %B %d, %Y')}."
