"""The :class:`Localizer` - JARVIS's single source of truth for language.

Responsibilities
----------------
- Resolve and validate the active language (``en`` / ``ru`` / ``de`` / ``ar``).
- Translate message keys to the active language with safe fallback to English.
- Expose the speech-recognition locale (e.g. ``ru-RU``) and a list of
  text-to-speech voice-name hints so the speaker can pick a matching voice.
- Provide right-to-left awareness for Arabic.
- Offer a small, dependency-free language guess for spoken/typed input so the
  assistant can optionally auto-switch languages.

The Localizer is intentionally immutable: switching language produces a new
instance via :meth:`with_language`. This keeps it safe to share between agents
and skills without surprising mutation.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from .strings import DEFAULT_LANGUAGE, RTL_LANGUAGES, TABLES

#: Human-readable, self-referential names (useful for UIs and prompts).
LANGUAGE_NAMES: Dict[str, str] = {
    "en": "English",
    "ru": "Русский",
    "de": "Deutsch",
    "ar": "العربية",
}

#: Map language -> the BCP-47 locale used by the speech recognizer.
STT_LOCALES: Dict[str, str] = {
    "en": "en-US",
    "ru": "ru-RU",
    "de": "de-DE",
    "ar": "ar-SA",
}

#: Substrings (lowercased) commonly found in SAPI5 / platform TTS voice names,
#: in priority order. The speaker matches these against installed voices.
TTS_VOICE_HINTS: Dict[str, List[str]] = {
    "en": ["english", "en-us", "en_us", "david", "zira", "mark"],
    "ru": ["russian", "ru-ru", "ru_ru", "irina", "pavel"],
    "de": ["german", "deutsch", "de-de", "de_de", "hedda", "stefan", "katja"],
    "ar": ["arabic", "ar-sa", "ar_sa", "naayf", "hoda"],
}

#: Cyrillic and Arabic Unicode ranges, used by the lightweight detector.
_CYRILLIC = re.compile(r"[\u0400-\u04FF]")
_ARABIC = re.compile(r"[\u0600-\u06FF]")

#: A few high-signal German tokens to disambiguate Latin-script input.
_GERMAN_MARKERS = re.compile(
    r"[äöüß]|\b(?:ich|und|nicht|öffne|öffnen|bitte|uhrzeit|lautstärke|wie|spät)\b",
    re.IGNORECASE,
)


class Localizer:
    """Translate message keys and expose language-specific speech settings."""

    def __init__(self, language: str = DEFAULT_LANGUAGE):
        self.language = self.normalize(language)

    # -- construction ---------------------------------------------------
    @staticmethod
    def normalize(language: Optional[str]) -> str:
        """Coerce arbitrary input (``"ru-RU"``, ``"DE"``, ``None``) to a code.

        Unknown or unsupported values fall back to the default language.
        """
        if not language:
            return DEFAULT_LANGUAGE
        code = str(language).strip().lower().replace("_", "-")
        # Accept full locales like "en-us" by taking the primary subtag.
        primary = code.split("-", 1)[0]
        if primary in TABLES:
            return primary
        return DEFAULT_LANGUAGE

    @classmethod
    def supported(cls) -> List[str]:
        """Return the list of supported language codes."""
        return list(TABLES.keys())

    def with_language(self, language: Optional[str]) -> "Localizer":
        """Return a new Localizer for ``language`` (or self if unchanged)."""
        new_lang = self.normalize(language)
        if new_lang == self.language:
            return self
        return Localizer(new_lang)

    # -- translation ----------------------------------------------------
    def t(self, key: str, **kwargs: object) -> str:
        """Translate ``key`` into the active language and interpolate ``kwargs``.

        Resolution order: active language -> English -> the raw key itself.
        Interpolation errors never raise; the unformatted template is returned
        so a translation bug degrades to readable text instead of a crash.
        """
        template = TABLES[self.language].get(key)
        if template is None:
            template = TABLES[DEFAULT_LANGUAGE].get(key, key)
        if not kwargs:
            return template
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return template

    # -- speech configuration ------------------------------------------
    @property
    def stt_locale(self) -> str:
        """BCP-47 locale string for the speech recognizer (e.g. ``de-DE``)."""
        return STT_LOCALES.get(self.language, STT_LOCALES[DEFAULT_LANGUAGE])

    @property
    def tts_voice_hints(self) -> List[str]:
        """Lowercased substrings to match against installed TTS voices."""
        return TTS_VOICE_HINTS.get(self.language, [])

    @property
    def is_rtl(self) -> bool:
        """True if the active language is written right-to-left (Arabic)."""
        return self.language in RTL_LANGUAGES

    @property
    def display_name(self) -> str:
        """Self-referential language name, e.g. ``Deutsch`` for German."""
        return LANGUAGE_NAMES.get(self.language, self.language)

    def affirmatives(self) -> List[str]:
        """Localized words/phrases that count as a 'yes' confirmation."""
        raw = self.t("safety.affirmatives")
        return [token.strip() for token in raw.split("|") if token.strip()]

    # -- detection ------------------------------------------------------
    @classmethod
    def detect(cls, text: str) -> Optional[str]:
        """Best-effort language guess for ``text`` without external deps.

        Uses Unicode script ranges (Cyrillic -> Russian, Arabic -> Arabic) and a
        few German markers for Latin-script disambiguation. Returns a supported
        language code or ``None`` when there isn't enough signal (caller should
        then keep the current language).
        """
        if not text or not text.strip():
            return None
        if _ARABIC.search(text):
            return "ar"
        if _CYRILLIC.search(text):
            return "ru"
        if _GERMAN_MARKERS.search(text):
            return "de"
        # Default Latin script with no German markers: assume English.
        if re.search(r"[a-zA-Z]", text):
            return "en"
        return None
