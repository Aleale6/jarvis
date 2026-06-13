"""The Assistant orchestrator: listen -> route -> respond.

Two run loops are provided:
    * ``run_voice()`` - wake-word driven voice interaction (the real JARVIS mode).
    * ``run_text()``  - type commands instead of speaking (handy for testing).
"""

from __future__ import annotations

from typing import List, Optional

from .brain.llm import LLMBrain
from .config import Config
from .skills.base import Skill, SkillContext, default_skills
from .speech.listener import Listener
from .speech.speaker import Speaker

_HELP_TRIGGERS = ["what can you do", "help", "your commands", "list commands"]


class Assistant:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.load()
        self.name = self.config.get("assistant_name", "Jarvis")
        self.wake_word = self.config.get("wake_word", "jarvis")
        self.exit_phrases = [p.lower() for p in self.config.get("exit_phrases", [])]

        self.speaker = Speaker(self.config.section("voice"))
        self.brain = LLMBrain(self.config.section("llm"))
        self.skills: List[Skill] = default_skills()
        self._ctx = SkillContext(config=self.config, speaker=self.speaker)
        self._running = False

    # -- command handling ----------------------------------------------
    def handle_command(self, command: str) -> bool:
        """Process one command. Returns False if the assistant should stop."""
        command = (command or "").strip().lower()
        if not command:
            self.speaker.say("I didn't catch that.")
            return True

        if self._is_exit(command):
            self.speaker.say("Powering down. Goodbye.")
            return False

        if self._contains_any(command, _HELP_TRIGGERS):
            self.speaker.say(self._help_text())
            return True

        # 1) Try built-in skills (first match wins).
        for skill in self.skills:
            try:
                if skill.matches(command):
                    reply = skill.run(command, self._ctx)
                    self.speaker.say(reply)
                    return True
            except Exception as exc:  # noqa: BLE001 - a broken skill shouldn't crash JARVIS
                print(f"[assistant] Skill '{skill.name}' error: {exc}")
                self.speaker.say("Sorry, something went wrong running that.")
                return True

        # 2) Fall back to the LLM brain for open-ended questions.
        if self.brain.enabled:
            reply = self.brain.ask(command)
            self.speaker.say(reply or "I'm not sure how to answer that.")
        else:
            self.speaker.say(
                "I can't answer open questions yet because no language model key "
                "is set. But I can tell the time, open apps, search the web, take "
                "notes, and control the volume."
            )
        return True

    # -- run loops ------------------------------------------------------
    def run_voice(self) -> None:
        if not self.listener_available():
            self.speaker.say(
                "I can't access a microphone, so I'll switch to text mode. "
                "Type your commands instead."
            )
            self.run_text()
            return

        self._running = True
        self.speaker.say(f"{self.name} online. Say '{self.wake_word}' followed by a command.")

        while self._running:
            heard, command = self._listener.wait_for_command()
            if not heard:
                continue
            if command is None:
                self.speaker.say("Yes?")
                command = self._listener.listen_once()
            keep_going = self.handle_command(command or "")
            if not keep_going:
                self._running = False

    def run_text(self) -> None:
        self.speaker.say(f"{self.name} online in text mode. Type a command, or 'quit' to stop.")
        while True:
            try:
                command = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                self.speaker.say("Goodbye.")
                break
            if not self.handle_command(command):
                break

    # -- helpers --------------------------------------------------------
    def listener_available(self) -> bool:
        self._listener = Listener(self.config.section("listener"), wake_word=self.wake_word)
        return self._listener.available

    def _is_exit(self, command: str) -> bool:
        return any(phrase and phrase in command for phrase in self.exit_phrases)

    @staticmethod
    def _contains_any(text: str, keywords: List[str]) -> bool:
        return any(kw in text for kw in keywords)

    def _help_text(self) -> str:
        abilities = [
            "tell the time and date",
            "open applications like notepad or chrome",
            "search the web and open websites",
            "take and read notes",
            "control the volume and lock the screen",
        ]
        if self.brain.enabled:
            abilities.append("answer general questions")
        return "I can " + ", ".join(abilities) + "."
