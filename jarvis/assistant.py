"""The Assistant orchestrator: listen -> understand -> gate -> respond.

This is the coordination layer that ties the subsystems together:
  * :class:`~jarvis.i18n.Localizer` - all user-facing text and speech config.
  * :class:`~jarvis.core.safety.SafetyManager` - gates system-affecting actions.
  * :class:`~jarvis.core.logging_setup.EventLogger` - structured audit trail.
  * skills + the multi-provider LLM brain - do the actual work.

Two run loops are provided:
    * ``run_voice()`` - wake-word driven voice interaction (the real JARVIS mode).
    * ``run_text()``  - type commands instead of speaking (handy for testing).

Multilingual behaviour
----------------------
The active language (en/ru/de/ar) comes from config. When
``auto_detect_language`` is on, each command is inspected and, if it is clearly
in a different supported language, the assistant switches the localizer, brain,
speaker voice, and recognition locale on the fly so the reply matches the user.
"""

from __future__ import annotations

from typing import List, Optional

from .brain.llm import LLMBrain
from .config import Config
from .core.logging_setup import EventLogger
from .core.safety import SafetyManager, SafetyRequest
from .i18n import Localizer
from .skills.base import Skill, SkillContext, default_skills
from .speech.listener import Listener
from .speech.speaker import Speaker

_HELP_TRIGGERS = ["what can you do", "help", "your commands", "list commands",
                  "что ты умеешь", "помощь", "was kannst du", "hilfe",
                  "ماذا تستطيع", "مساعدة"]


class Assistant:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.load()
        self.name = self.config.get("assistant_name", "Jarvis")
        self.wake_word = self.config.get("wake_word", "jarvis")
        self.auto_detect = bool(self.config.get("auto_detect_language", True))

        # Localization first - everything else takes it as input.
        self.localizer = Localizer(self.config.get("language", "en"))

        # Structured logging + safety policy.
        log_cfg = self.config.section("logging")
        self.logger = EventLogger(
            log_path=log_cfg.get("file") or None,
            echo_console=bool(log_cfg.get("echo_console", True)),
        )
        self.safety = SafetyManager.from_config(self.config.section("safety"), logger=self.logger)

        # Speech + brain (both language-aware).
        self.speaker = Speaker(self.config.section("voice"), localizer=self.localizer)
        self.brain = LLMBrain(self.config.section("llm"), localizer=self.localizer)

        self.exit_phrases = self._exit_phrases()
        self.skills: List[Skill] = default_skills()
        self._listener: Optional[Listener] = None
        self._running = False
        self._mode = "text"  # set to "voice" by run_voice

        self.logger.info(
            agent="assistant", action="startup", result="ok",
            language=self.localizer.language,
            providers=[p.name for p in self.brain._router.providers],  # noqa: SLF001
        )

    # -- context building ----------------------------------------------
    def _make_context(self) -> SkillContext:
        return SkillContext(
            config=self.config,
            speaker=self.speaker,
            localizer=self.localizer,
            safety=self.safety,
            logger=self.logger,
            confirm=self._confirm,
        )

    # -- command handling ----------------------------------------------
    def handle_command(self, command: str) -> bool:
        """Process one command. Returns False if the assistant should stop."""
        command = (command or "").strip().lower()
        if not command:
            self.speaker.say(self.localizer.t("assistant.not_understood"))
            return True

        self._maybe_switch_language(command)
        self.logger.info(agent="assistant", action="command", result="received",
                         language=self.localizer.language)

        if self._is_exit(command):
            self.speaker.say(self.localizer.t("assistant.powering_down"))
            self.logger.info(agent="assistant", action="shutdown", result="ok")
            return False

        if self._contains_any(command, _HELP_TRIGGERS):
            self.speaker.say(self._help_text())
            return True

        ctx = self._make_context()

        # 1) Try built-in skills (first match wins).
        for skill in self.skills:
            try:
                if skill.matches(command):
                    reply = skill.run(command, ctx)
                    self.speaker.say(reply)
                    return True
            except Exception as exc:  # noqa: BLE001 - a broken skill shouldn't crash JARVIS
                self.logger.error(agent="skill", action=skill.name, error=str(exc))
                self.speaker.say(self.localizer.t("assistant.skill_error"))
                return True

        # 2) Fall back to the LLM brain for open-ended questions.
        if self.brain.enabled:
            reply = self.brain.ask(command)
            self.speaker.say(reply or self.localizer.t("assistant.llm_unsure"))
        else:
            self.speaker.say(self.localizer.t("assistant.no_llm"))
        return True

    # -- language ------------------------------------------------------
    def _maybe_switch_language(self, command: str) -> None:
        """Auto-switch the active language if the command is clearly in another.

        Detection is only acted on when it carries a *positive* signal:
        Cyrillic -> Russian and Arabic script -> Arabic are unambiguous, and
        German is detected via marker words. English and German share the Latin
        script, so a plain-Latin command (which the detector labels ``en``) is
        ambiguous: we must NOT switch a German session to English just because a
        word like "hilfe" lacks an umlaut. The guard below keeps the current
        language in that ambiguous case.
        """
        if not self.auto_detect:
            return
        detected = Localizer.detect(command)
        current = self.localizer.language
        if not detected or detected == current:
            return
        # Ambiguous Latin: don't drop from German to English without a real cue.
        if detected == "en" and current == "de":
            return
        self._set_language(detected)

    def _set_language(self, language: str) -> None:
        """Switch every language-dependent subsystem to ``language``."""
        self.localizer = self.localizer.with_language(language)
        self.brain.set_language(self.localizer.language)
        self.speaker.set_localizer(self.localizer)
        self.exit_phrases = self._exit_phrases()
        if self._listener is not None:
            self._listener.set_language(self.localizer.stt_locale)
        self.logger.info(agent="assistant", action="switch_language",
                         result="ok", language=self.localizer.language)

    # -- confirmation (safety pipeline) --------------------------------
    def _confirm(self, request: SafetyRequest) -> bool:
        """Ask the user to approve a gated action; return True if they agree.

        Used as the confirm callback for the :class:`SafetyManager`. Prompts in
        the active language and accepts a localized affirmative.
        """
        phrase = request.description or request.action
        prompt = self.localizer.t("safety.confirm", action=phrase)
        self.speaker.say(prompt)

        answer = self._get_confirmation_input()
        affirmatives = self.localizer.affirmatives()
        approved = bool(answer) and any(word in answer for word in affirmatives)
        self.speaker.say(
            self.localizer.t("safety.confirmed" if approved else "safety.cancelled")
        )
        return approved

    def _get_confirmation_input(self) -> str:
        """Capture a yes/no answer via mic (voice mode) or stdin (text mode)."""
        if self._mode == "voice" and self._listener is not None and self._listener.available:
            return (self._listener.listen_once() or "").strip().lower()
        try:
            return input("Confirm? ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return ""

    # -- run loops ------------------------------------------------------
    def run_voice(self) -> None:
        self._mode = "voice"
        if not self.listener_available():
            self.speaker.say(self.localizer.t("assistant.no_mic"))
            self.run_text()
            return

        self._running = True
        self.speaker.say(
            self.localizer.t("assistant.online_voice", name=self.name, wake_word=self.wake_word)
        )

        while self._running:
            heard, command = self._listener.wait_for_command()
            if not heard:
                continue
            if command is None:
                self.speaker.say(self.localizer.t("assistant.yes"))
                command = self._listener.listen_once()
            keep_going = self.handle_command(command or "")
            if not keep_going:
                self._running = False

    def run_text(self) -> None:
        self._mode = "text"
        self.speaker.say(
            self.localizer.t("assistant.online_text", name=self.name, quit="quit")
        )
        while True:
            try:
                command = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                self.speaker.say(self.localizer.t("assistant.goodbye"))
                break
            if not self.handle_command(command):
                break

    # -- helpers --------------------------------------------------------
    def listener_available(self) -> bool:
        self._listener = Listener(
            self.config.section("listener"),
            wake_word=self.wake_word,
            language=self.localizer.stt_locale,
        )
        return self._listener.available

    def _exit_phrases(self) -> List[str]:
        """Localized exit phrases, merged with any configured in config.json."""
        localized = [p.strip() for p in self.localizer.t("exit.phrases").split("|") if p.strip()]
        configured = [str(p).lower() for p in self.config.get("exit_phrases", []) or []]
        # Preserve order, drop duplicates.
        seen, merged = set(), []
        for phrase in localized + configured:
            if phrase and phrase not in seen:
                seen.add(phrase)
                merged.append(phrase)
        return merged

    def _is_exit(self, command: str) -> bool:
        return any(phrase and phrase in command for phrase in self.exit_phrases)

    @staticmethod
    def _contains_any(text: str, keywords: List[str]) -> bool:
        return any(kw in text for kw in keywords)

    def _help_text(self) -> str:
        keys = ["help.time", "help.apps", "help.web", "help.notes", "help.system"]
        if self.brain.enabled:
            keys.append("help.general")
        abilities = [self.localizer.t(k) for k in keys]
        join = self.localizer.t("assistant.help_join")
        return self.localizer.t("assistant.help_prefix") + join.join(abilities) + "."
