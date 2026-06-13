"""Open websites and run web searches in the default browser (multilingual)."""

from __future__ import annotations

import webbrowser
from urllib.parse import quote_plus

from ..core.safety import RiskLevel, SafetyRequest
from ..i18n.triggers import matches_any, starts_with_verb, strip_trigger
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


class WebSkill(Skill):
    name = "web"
    description = "Open a website or search the web."

    def matches(self, text: str) -> bool:
        target = starts_with_verb(text)
        if target and self._target_is_site(target):
            return True
        return matches_any(text, "web.search")

    def _target_is_site(self, target: str) -> bool:
        return (
            target in _KNOWN_SITES
            or target.endswith(".com")
            or target.endswith(".org")
            or target.startswith("http")
        )

    def run(self, text: str, ctx: SkillContext) -> str:
        # 1) "open youtube" / "öffne github.com"
        target = starts_with_verb(text)
        if target and self._target_is_site(target):
            url = self._resolve_site(target)
            if not self._gate(ctx, action=f"open website {target}", url=url):
                return ctx.t("safety.cancelled")
            webbrowser.open(url)
            ctx.logger.info(agent="web", action="open_site", result="ok", url=url)
            return ctx.t("skill.web.opening", target=target)

        # 2) a web search
        query = strip_trigger(text, "web.search")
        if not query:
            return ctx.t("skill.web.what")
        search_url = f"https://www.google.com/search?q={quote_plus(query)}"
        if not self._gate(ctx, action=f"search the web for {query}", url=search_url):
            return ctx.t("safety.cancelled")
        webbrowser.open(search_url)
        ctx.logger.info(agent="web", action="web_search", result="ok")
        return ctx.t("skill.web.searching", query=query)

    @staticmethod
    def _gate(ctx: SkillContext, action: str, url: str) -> bool:
        """Gate a browser action through the safety pipeline (category 'web')."""
        request = SafetyRequest(
            agent="web",
            action=action,
            category="web",
            risk=RiskLevel.LOW,
            reversible=True,
            detail={"url": url},
        )
        return ctx.safety.authorize(request, confirm=ctx.confirm)

    @staticmethod
    def _resolve_site(target: str) -> str:
        if target in _KNOWN_SITES:
            return _KNOWN_SITES[target]
        if target.startswith("http"):
            return target
        return f"https://{target}"
