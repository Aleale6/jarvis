"""Control the PC: launch applications and adjust system volume (Windows 10)."""

from __future__ import annotations

import os
import subprocess
import sys

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
        if text.startswith("open ") or text.startswith("launch ") or text.startswith("start "):
            return True
        if "volume" in text or text in ("mute", "unmute"):
            return True
        if self._contains_any(text, ["lock the screen", "lock screen", "lock my pc", "lock computer"]):
            return True
        return False

    def run(self, text: str, ctx: SkillContext) -> str:
        if self._contains_any(text, ["lock the screen", "lock screen", "lock my pc", "lock computer"]):
            return self._lock_screen()

        if "volume" in text or text in ("mute", "unmute"):
            return self._handle_volume(text)

        # otherwise it's an app-launch request
        for prefix in ("open ", "launch ", "start "):
            if text.startswith(prefix):
                app = text[len(prefix):].strip()
                return self._open_app(app)
        return "I'm not sure what to open."

    # -- applications ---------------------------------------------------
    def _open_app(self, app: str) -> str:
        if not app:
            return "Which application should I open?"
        command = _KNOWN_APPS.get(app, app)
        try:
            # shell=True lets Windows resolve names on PATH and start verbs.
            subprocess.Popen(command, shell=True)
            return f"Opening {app}."
        except Exception as exc:  # noqa: BLE001
            return f"Sorry, I couldn't open {app} ({exc})."

    # -- volume ---------------------------------------------------------
    def _handle_volume(self, text: str) -> str:
        if not sys.platform.startswith("win"):
            return "Volume control is only wired up for Windows right now."

        if "mute" in text and "unmute" not in text:
            self._tap_key(_VK_VOLUME_MUTE)
            return "Muted."
        if "unmute" in text:
            self._tap_key(_VK_VOLUME_MUTE)  # mute key toggles
            return "Unmuted."
        if self._contains_any(text, ["up", "increase", "raise", "louder"]):
            for _ in range(5):  # each tap is ~2%, so ~10% per command
                self._tap_key(_VK_VOLUME_UP)
            return "Turning the volume up."
        if self._contains_any(text, ["down", "decrease", "lower", "quieter", "reduce"]):
            for _ in range(5):
                self._tap_key(_VK_VOLUME_DOWN)
            return "Turning the volume down."
        return "Say volume up, volume down, or mute."

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
    @staticmethod
    def _lock_screen() -> str:
        if not sys.platform.startswith("win"):
            return "Locking the screen is only supported on Windows here."
        try:
            ctypes_ok = os.system("rundll32.exe user32.dll,LockWorkStation") == 0
            return "Locking the screen." if ctypes_ok else "Sorry, I couldn't lock the screen."
        except Exception as exc:  # noqa: BLE001
            return f"Sorry, I couldn't lock the screen ({exc})."
