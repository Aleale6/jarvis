"""Internationalization (i18n) for JARVIS.

Supports English (``en``), Russian (``ru``), German (``de``), and Arabic
(``ar``). The :class:`Localizer` is the public entry point; translation tables
live in :mod:`jarvis.i18n.strings`.
"""

from .locale import LANGUAGE_NAMES, Localizer
from .strings import DEFAULT_LANGUAGE, RTL_LANGUAGES

__all__ = ["Localizer", "LANGUAGE_NAMES", "DEFAULT_LANGUAGE", "RTL_LANGUAGES"]
