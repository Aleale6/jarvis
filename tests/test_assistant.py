"""End-to-end tests for the Assistant: localization + skill routing + safety."""

from __future__ import annotations

import pytest

from jarvis.assistant import Assistant
from jarvis.config import Config


class FakeSpeaker:
    """Captures spoken lines instead of using TTS."""

    def __init__(self):
        self.lines = []

    def say(self, text):
        if text:
            self.lines.append(text)

    def set_localizer(self, _localizer):
        pass

    @property
    def last(self):
        return self.lines[-1] if self.lines else ""


def make_assistant(language="en", auto_confirm=True, granted=None, blocked=None):
    cfg = Config.load()
    cfg.data["language"] = language
    cfg.data["logging"]["file"] = None
    cfg.data["logging"]["echo_console"] = False
    cfg.data["safety"]["auto_confirm"] = auto_confirm
    cfg.data["safety"]["granted_permissions"] = granted or []
    cfg.data["safety"]["blocked_permissions"] = blocked or []
    a = Assistant(cfg)
    a.speaker = FakeSpeaker()
    return a


def test_time_skill_english():
    a = make_assistant("en")
    a.handle_command("what time is it")
    assert a.speaker.last.startswith("It's")


def test_time_skill_russian_autodetect():
    a = make_assistant("en")
    a.handle_command("который час")
    assert a.localizer.language == "ru"
    assert a.speaker.last.startswith("Сейчас")


def test_time_skill_arabic_autodetect():
    a = make_assistant("en")
    a.handle_command("كم الساعة")
    assert a.localizer.language == "ar"
    assert "الساعة" in a.speaker.last


def test_open_app_blocked_category_is_denied():
    a = make_assistant("en", auto_confirm=True, blocked=["app_control"])
    a.handle_command("open notepad")
    # Denied by policy -> localized denial message, not "Opening".
    assert a.speaker.last == a.localizer.t("safety.denied")


def test_open_app_requires_confirmation_and_declines():
    # auto_confirm off + an empty/negative confirmation answer -> cancelled
    a = make_assistant("en", auto_confirm=False)
    a._get_confirmation_input = lambda: ""  # simulate no/empty answer
    a.handle_command("open notepad")
    assert a.speaker.last == a.localizer.t("safety.cancelled")


def test_open_app_granted_proceeds():
    a = make_assistant("en", auto_confirm=False, granted=["app_control"])
    a.handle_command("open notepad")
    assert a.speaker.last == a.localizer.t("skill.system.opening", app="notepad")


def test_help_text_localized_german():
    a = make_assistant("de")
    a.handle_command("hilfe")
    assert a.speaker.last.startswith("Ich kann")


def test_exit_command_returns_false():
    a = make_assistant("en")
    keep_going = a.handle_command("goodbye")
    assert keep_going is False


def test_exit_command_localized_russian():
    a = make_assistant("ru")
    keep_going = a.handle_command("пока")
    assert keep_going is False


def test_empty_command_prompts_again():
    a = make_assistant("en")
    keep_going = a.handle_command("   ")
    assert keep_going is True
    assert a.speaker.last == a.localizer.t("assistant.not_understood")


def test_confirmation_callback_accepts_localized_yes():
    a = make_assistant("ru", auto_confirm=False)
    # Simulate the user answering with a Russian affirmative.
    a._get_confirmation_input = lambda: "да"
    a.handle_command("открой блокнот")
    assert a.speaker.last == a.localizer.t("skill.system.opening", app="блокнот")
