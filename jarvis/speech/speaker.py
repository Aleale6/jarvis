"""Text-to-speech output using pyttsx3 (offline Windows SAPI5 voices)."""

from __future__ import annotations

from typing import Any, Dict, Optional


class Speaker:
    """Wraps a pyttsx3 engine and degrades gracefully to printing if TTS fails."""

    def __init__(self, voice_cfg: Optional[Dict[str, Any]] = None):
        voice_cfg = voice_cfg or {}
        self._engine = None
        try:
            import pyttsx3  # imported lazily so the package imports without it

            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", int(voice_cfg.get("rate", 175)))
            self._engine.setProperty("volume", float(voice_cfg.get("volume", 1.0)))

            voice_index = voice_cfg.get("voice_index")
            if voice_index is not None:
                voices = self._engine.getProperty("voices") or []
                if 0 <= int(voice_index) < len(voices):
                    self._engine.setProperty("voice", voices[int(voice_index)].id)
        except Exception as exc:  # noqa: BLE001 - any TTS failure should not crash
            print(f"[speaker] Text-to-speech unavailable ({exc}). Falling back to text.")
            self._engine = None

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
