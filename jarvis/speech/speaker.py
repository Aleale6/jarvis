"""Text-to-speech output using pyttsx3 (offline Windows SAPI5 voices).

The speaker is language-aware: given a :class:`~jarvis.i18n.Localizer`, it tries
to select an installed voice whose name matches the active language (e.g. a
Russian or German SAPI5 voice). If no matching voice is installed it falls back
to the configured ``voice_index`` so speech still works, just in the default
voice. All TTS failures degrade gracefully to printing the text.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class Speaker:
    """Wraps a pyttsx3 engine and degrades gracefully to printing if TTS fails."""

    def __init__(self, voice_cfg: Optional[Dict[str, Any]] = None, localizer: Optional[Any] = None):
        voice_cfg = voice_cfg or {}
        self._cfg = voice_cfg
        self._localizer = localizer
        self._engine = None
        try:
            import pyttsx3  # imported lazily so the package imports without it

            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", int(voice_cfg.get("rate", 175)))
            self._engine.setProperty("volume", float(voice_cfg.get("volume", 1.0)))
            self._select_voice()
        except Exception as exc:  # noqa: BLE001 - any TTS failure should not crash
            print(f"[speaker] Text-to-speech unavailable ({exc}). Falling back to text.")
            self._engine = None

    # -- voice selection ------------------------------------------------
    def _select_voice(self) -> None:
        """Pick a voice that matches the active language, else the config index."""
        if self._engine is None:
            return
        voices = self._engine.getProperty("voices") or []
        if not voices:
            return

        # 1) Try to match the active language by voice-name hints.
        hints = self._language_hints()
        if hints:
            for voice in voices:
                haystack = f"{getattr(voice, 'name', '')} {getattr(voice, 'id', '')}".lower()
                languages = self._voice_languages(voice)
                if any(hint in haystack for hint in hints) or any(
                    hint in lang for hint in hints for lang in languages
                ):
                    self._engine.setProperty("voice", voice.id)
                    return

        # 2) Fall back to the configured index.
        voice_index = self._cfg.get("voice_index")
        if voice_index is not None and 0 <= int(voice_index) < len(voices):
            self._engine.setProperty("voice", voices[int(voice_index)].id)

    def _language_hints(self) -> List[str]:
        if self._localizer is None:
            return []
        try:
            return list(self._localizer.tts_voice_hints)
        except AttributeError:
            return []

    @staticmethod
    def _voice_languages(voice: Any) -> List[str]:
        """Best-effort decode of a SAPI5 voice's advertised languages."""
        langs = getattr(voice, "languages", None) or []
        decoded: List[str] = []
        for lang in langs:
            try:
                decoded.append(lang.decode("utf-8", "ignore").lower() if isinstance(lang, bytes) else str(lang).lower())
            except Exception:  # noqa: BLE001
                continue
        return decoded

    def set_localizer(self, localizer: Any) -> None:
        """Switch language and re-select a matching voice at runtime."""
        self._localizer = localizer
        self._select_voice()

    # -- speech ---------------------------------------------------------
    def say(self, text: str) -> None:
        """Speak ``text`` aloud (and always echo it to the console)."""
        if not text:
            return
        print(f"JARVIS: {text}")
        if self._engine is None:
            return
        try:
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception as exc:  # noqa: BLE001
            print(f"[speaker] Could not speak ({exc}).")

    def list_voices(self) -> None:
        """Print the installed SAPI5 voices and their indexes (handy for config)."""
        if self._engine is None:
            print("[speaker] No TTS engine available.")
            return
        voices = self._engine.getProperty("voices") or []
        for idx, voice in enumerate(voices):
            print(f"  [{idx}] {voice.name} ({voice.id})")
