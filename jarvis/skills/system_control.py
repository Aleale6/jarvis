"""Control the PC: launch applications and adjust system volume (Windows 10).

Every action that changes machine state is routed through the safety pipeline
(:class:`~jarvis.core.safety.SafetyManager`) before it runs. Launching apps is
the ``app_control`` category; volume, mute, and screen lock are
``system_settings``. Both are MEDIUM risk and reversible, so they are allowed
outright only when the user has pre-authorized that category - otherwise the
user is asked to confirm. All outcomes are logged.
"""

from __future__ import annotations

import os
import subprocess
import sys

from ..core.safety import Decision, RiskLevel, SafetyRequest
from ..i18n.triggers import matches_any, starts_with_verb
from .base import Skill, SkillContext

# Spoken name -> executable/command launched via the shell.
_KNOWN_APPS = {
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "paint": "mspaint",
    "command prompt": "cmd",
    "cmd": "cmd",
    "explorer": "explorer",
    "file explorer": "explorer",
    "task manager": "taskmgr",
    "control panel": "control",
    "settings": "start ms-settings:",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "chrome": "chrome",
    "edge": "msedge",
    "firefox": "firefox",
    "spotify": "spotify",
}

# Virtual-key codes for the media volume keys (Windows).
_VK_VOLUME_MUTE = 0xAD
_VK_VOLUME_DOWN = 0xAE
_VK_VOLUME_UP = 0xAF


class SystemControlSkill(Skill):
    name = "system_control"
    description = "Open applications and control the volume."

    def matches(self, text: str) -> bool:
        if matches_any(text, "system.lock"):
            return True
        if matches_any(text, "volume.any"):
            return True
        if starts_with_verb(text):  # an "open/launch/öffne ..." command
            return True
        return False

    def run(self, text: str, ctx: SkillContext) -> str:
        if matches_any(text, "system.lock"):
            return self._lock_screen(ctx)

        if matches_any(text, "volume.any"):
            return self._handle_volume(text, ctx)

        # otherwise it's an app-launch request
        app = starts_with_verb(text)
        if app:
            return self._open_app(app, ctx)
        return ctx.t("skill.system.unsure_open")

    # -- safety helper --------------------------------------------------
    def _gate(
        self,
        ctx: SkillContext,
        action: str,
        category: str,
        description: str,
    ) -> Decision:
        """Run a MEDIUM-risk, reversible system action through the gate."""
        request = SafetyRequest(
            agent="system_control",
            action=action,
            category=category,
            risk=RiskLevel.MEDIUM,
            reversible=True,
            description=description,
        )
        return ctx.safety.gate(request, confirm=ctx.confirm)

    @staticmethod
    def _refusal_message(ctx: SkillContext, decision: Decision) -> str:
        """Localized reply for a non-ALLOW decision."""
        if decision is Decision.DENY:
            return ctx.t("safety.denied")
        return ctx.t("safety.cancelled")

    # -- applications ---------------------------------------------------
    def _open_app(self, app: str, ctx: SkillContext) -> str:
        if not app:
            return ctx.t("skill.system.which_app")

        decision = self._gate(
            ctx,
            action=f"open app: {app}",
            category="app_control",
            description=ctx.t("skill.system.action_open", app=app),
        )
        if decision is not Decision.ALLOW:
            return self._refusal_message(ctx, decision)

        command = _KNOWN_APPS.get(app, app)
        try:
            # shell=True lets Windows resolve names on PATH and start verbs.
            subprocess.Popen(command, shell=True)
            ctx.logger.info(agent="system_control", action="open_app", result="ok", app=app)
            return ctx.t("skill.system.opening", app=app)
        except Exception as exc:  # noqa: BLE001
            ctx.logger.error(agent="system_control", action="open_app", error=str(exc), app=app)
            return ctx.t("skill.system.open_failed", app=app, error=exc)

    # -- volume ---------------------------------------------------------
    def _handle_volume(self, text: str, ctx: SkillContext) -> str:
        if not sys.platform.startswith("win"):
            return ctx.t("skill.system.volume_win_only")

        decision = self._gate(
            ctx,
            action="adjust volume",
            category="system_settings",
            description=ctx.t("skill.system.volume_help"),
        )
        if decision is not Decision.ALLOW:
            return self._refusal_message(ctx, decision)

        if matches_any(text, "volume.unmute"):
            self._tap_key(_VK_VOLUME_MUTE)  # mute key toggles
            return ctx.t("skill.system.unmuted")
        if matches_any(text, "volume.mute"):
            self._tap_key(_VK_VOLUME_MUTE)
            return ctx.t("skill.system.muted")
        if matches_any(text, "volume.up"):
            for _ in range(5):  # each tap is ~2%, so ~10% per command
                self._tap_key(_VK_VOLUME_UP)
            return ctx.t("skill.system.volume_up")
        if matches_any(text, "volume.down"):
            for _ in range(5):
                self._tap_key(_VK_VOLUME_DOWN)
            return ctx.t("skill.system.volume_down")
        return ctx.t("skill.system.volume_help")

    @staticmethod
    def _tap_key(vk_code: int) -> None:
        """Press and release a virtual key via the Win32 API (no extra deps)."""
        try:
            import ctypes

            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
            user32.keybd_event(vk_code, 0, 0, 0)  # key down
            user32.keybd_event(vk_code, 0, 2, 0)  # key up (KEYEVENTF_KEYUP)
        except Exception as exc:  # noqa: BLE001
            print(f"[system] Volume key error ({exc}).")

    # -- screen lock ----------------------------------------------------
    def _lock_screen(self, ctx: SkillContext) -> str:
        if not sys.platform.startswith("win"):
            return ctx.t("skill.system.lock_win_only")

        decision = self._gate(
            ctx,
            action="lock screen",
            category="system_settings",
            description=ctx.t("skill.system.action_lock"),
        )
        if decision is not Decision.ALLOW:
            return self._refusal_message(ctx, decision)

        try:
            ok = os.system("rundll32.exe user32.dll,LockWorkStation") == 0
            if ok:
                ctx.logger.info(agent="system_control", action="lock_screen", result="ok")
                return ctx.t("skill.system.locking")
            ctx.logger.warning(agent="system_control", action="lock_screen", result="failed")
            return ctx.t("skill.system.lock_failed")
        except Exception as exc:  # noqa: BLE001
            ctx.logger.error(agent="system_control", action="lock_screen", error=str(exc))
            return ctx.t("skill.system.lock_failed")
