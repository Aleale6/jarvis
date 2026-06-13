"""Open websites and run web searches in the default browser."""

from __future__ import annotations

import webbrowser
from urllib.parse import quote_plus

from .base import Skill, SkillContext

# Friendly name -> URL for common sites the user can "open by name".
_KNOWN_SITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "wikipedia": "https://www.wikipedia.org",
    "maps": "https://maps.google.com",
    "reddit": "https://www.reddit.com",
    "stack overflow": "https://stackoverflow.com",
    "stackoverflow": "https://stackoverflow.com",
}

_SEARCH_TRIGGERS = ["search the web for", "search for", "google", "search", "look up", "what is", "who is"]


class WebSkill(Skill):
    name = "web"
    description = "Open a website or search the web."

    def matches(self, text: str) -> bool:
        if text.startswith("open ") and self._target_is_site(text):
            return True
        return self._contains_any(text, _SEARCH_TRIGGERS)

    def _target_is_site(self, text: str) -> bool:
        target = text[len("open "):].strip()
        return target in _KNOWN_SITES or target.endswith(".com") or target.endswith(".org") or target.startswith("http")

    def run(self, text: str, ctx: SkillContext) -> str:
        # 1) "open youtube" / "open github.com"
        if text.startswith("open ") and self._target_is_site(text):
            target = text[len("open "):].strip()
            url = self._resolve_site(target)
            webbrowser.open(url)
            return f"Opening {target}."

        # 2) a web search
        query = self._extract_query(text)
        if not query:
            return "What would you like me to search for?"
        webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")
        return f"Searching the web for {query}."

    @staticmethod
    def _resolve_site(target: str) -> str:
        if target in _KNOWN_SITES:
            return _KNOWN_SITES[target]
        if target.startswith("http"):
            return target
        return f"https://{target}"

    @staticmethod
    def _extract_query(text: str) -> str:
        query = text
        for trigger in _SEARCH_TRIGGERS:
            if trigger in query:
                query = query.split(trigger, 1)[1]
                break
        return query.strip(" ?.")
