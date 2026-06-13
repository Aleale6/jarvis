"""Speech-to-text input with wake-word handling.

Uses the SpeechRecognition library with Google's free web recognizer (needs an
internet connection). The microphone is captured via PyAudio.

Two listening helpers are provided:
    * ``listen_once()``  - capture a single utterance and return the transcript.
    * ``wait_for_command()`` - block until the wake word is heard, then return the
      command text that followed it (or capture a follow-up utterance).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


class Listener:
    def __init__(
        self,
        listener_cfg: Optional[Dict[str, Any]] = None,
        wake_word: str = "jarvis",
        language: Optional[str] = None,
    ):
        cfg = listener_cfg or {}
        self.wake_word = (wake_word or "jarvis").strip().lower()
        # An explicit ``language`` (e.g. the active locale "de-DE") overrides the
        # static config value, so the recognizer follows the assistant's language.
        self.language = language or cfg.get("language", "en-US")
        self.phrase_time_limit = cfg.get("phrase_time_limit", 8)

        self._sr = None
        self._recognizer = None
        self._mic = None

        try:
            import speech_recognition as sr

            self._sr = sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = cfg.get("energy_threshold", 300)
            self._recognizer.dynamic_energy_threshold = cfg.get("dynamic_energy", True)
            self._recognizer.pause_threshold = cfg.get("pause_threshold", 0.8)
            self._mic = sr.Microphone()
            self._calibrate()
        except Exception as exc:  # noqa: BLE001
            print(f"[listener] Microphone/recognizer unavailable ({exc}).")
            self._recognizer = None
            self._mic = None

    @property
    def available(self) -> bool:
        return self._recognizer is not None and self._mic is not None

    def set_language(self, language: str) -> None:
        """Update the recognition locale (e.g. ``ru-RU``) at runtime."""
        if language:
            self.language = language

    def _calibrate(self) -> None:
        """Sample ambient noise once so recognition adapts to the room."""
        try:
            with self._mic as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.7)
        except Exception as exc:  # noqa: BLE001
            print(f"[listener] Ambient calibration skipped ({exc}).")

    def listen_once(self) -> Optional[str]:
        """Capture one utterance and return the lowercased transcript, or None."""
        if not self.available:
            return None
        try:
            with self._mic as source:
                audio = self._recognizer.listen(
                    source, phrase_time_limit=self.phrase_time_limit
                )
        except Exception as exc:  # noqa: BLE001
            print(f"[listener] Capture error ({exc}).")
            return None

        try:
            text = self._recognizer.recognize_google(audio, language=self.language)
            return text.strip().lower()
        except self._sr.UnknownValueError:
            return None  # speech was unintelligible
        except self._sr.RequestError as exc:
            print(f"[listener] Recognition service error ({exc}).")
            return None

    def wait_for_command(self) -> Tuple[bool, Optional[str]]:
        """Listen until the wake word is detected.

        Returns ``(heard_wake_word, command_text)``:
          * If the user said "jarvis open notepad", returns (True, "open notepad").
          * If the user said just "jarvis", returns (True, None) so the caller can
            prompt and capture a follow-up command.
          * If no wake word was heard this round, returns (False, None).
        """
        text = self.listen_once()
        if not text:
            return (False, None)

        if self.wake_word in text:
            command = text.split(self.wake_word, 1)[1].strip()
            # strip a leading comma/filler left after the wake word
            command = command.lstrip(",. ").strip()
            return (True, command or None)

        return (False, None)
