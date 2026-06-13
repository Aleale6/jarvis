"""Multilingual command triggers for rule-based skills.

The localized *replies* live in :mod:`jarvis.i18n.strings`; this module holds the
*input* side - the words a user can say in each supported language to invoke a
skill. Because the active language is detected per-utterance but users sometimes
mix languages (e.g. say an English app name in a German session), matching is
done against the **union** of all languages' triggers via :func:`phrases`. The
reply is still rendered in the active language, so recognition is forgiving
while output stays consistent.

Each intent maps to per-language phrase lists. Phrases are matched
case-insensitively as substrings (for keywords) or prefixes (for verbs like
"open"). Keeping triggers here - not scattered through skills - means adding a
language or tuning recognition is a single-file change.
"""

from __future__ import annotations

from typing import Dict, List

# intent -> { language -> [trigger phrases] }
_TRIGGERS: Dict[str, Dict[str, List[str]]] = {
    # --- time / date -----------------------------------------------------
    "time.time": {
        "en": ["what time", "the time", "current time", "tell me the time"],
        "ru": ["который час", "сколько времени", "текущее время", "скажи время"],
        "de": ["wie spät", "wie viel uhr", "die uhrzeit", "aktuelle zeit"],
        "ar": ["كم الساعة", "ما الوقت", "الوقت الآن", "كم الوقت"],
    },
    "time.date": {
        "en": ["what day", "what's the date", "what is the date", "today's date", "what date"],
        "ru": ["какое сегодня число", "какой сегодня день", "какая дата", "сегодняшняя дата"],
        "de": ["welches datum", "welcher tag", "das datum", "welcher wochentag"],
        "ar": ["ما التاريخ", "ما هو اليوم", "تاريخ اليوم", "اي يوم"],
    },
    # --- notes -----------------------------------------------------------
    "notes.take": {
        "en": ["take a note", "make a note", "note that", "remember that", "add a note"],
        "ru": ["запиши", "сделай заметку", "заметка", "запомни", "добавь заметку"],
        "de": ["notiz machen", "notiere", "merke dir", "schreib auf", "neue notiz"],
        "ar": ["دوّن ملاحظة", "سجل ملاحظة", "تذكر أن", "أضف ملاحظة", "دون"],
    },
    "notes.read": {
        "en": ["read my notes", "read notes", "what are my notes", "list my notes"],
        "ru": ["прочитай заметки", "прочитай мои заметки", "мои заметки", "покажи заметки"],
        "de": ["notizen vorlesen", "meine notizen", "lies meine notizen", "zeig notizen"],
        "ar": ["اقرأ ملاحظاتي", "ملاحظاتي", "اعرض ملاحظاتي", "اقرأ الملاحظات"],
    },
    # --- web -------------------------------------------------------------
    "web.search": {
        "en": ["search the web for", "search for", "google", "search", "look up"],
        "ru": ["найди в интернете", "найди", "загугли", "поиск", "поищи"],
        "de": ["suche im web nach", "suche nach", "google", "suche", "finde"],
        "ar": ["ابحث في الويب عن", "ابحث عن", "ابحث", "بحث", "جوجل"],
    },
    # --- system: open application ---------------------------------------
    # Verbs that start an "open X" command; the remainder is the target.
    "open.verbs": {
        "en": ["open", "launch", "start", "run"],
        "ru": ["открой", "открыть", "запусти", "запустить", "открывай"],
        "de": ["öffne", "öffnen", "starte", "start", "führe aus"],
        "ar": ["افتح", "شغل", "ابدأ", "تشغيل"],
    },
    # --- system: volume --------------------------------------------------
    "volume.any": {
        "en": ["volume", "mute", "unmute", "louder", "quieter"],
        "ru": ["громкость", "громче", "тише", "без звука", "выключи звук", "включи звук"],
        "de": ["lautstärke", "lauter", "leiser", "stumm", "stummschaltung"],
        "ar": ["مستوى الصوت", "الصوت", "ارفع الصوت", "اخفض الصوت", "كتم", "إلغاء الكتم"],
    },
    "volume.up": {
        "en": ["up", "increase", "raise", "louder"],
        "ru": ["громче", "увеличь", "повыс", "прибавь"],
        "de": ["lauter", "erhöhe", "höher"],
        "ar": ["ارفع", "زد", "أعلى"],
    },
    "volume.down": {
        "en": ["down", "decrease", "lower", "quieter", "reduce"],
        "ru": ["тише", "уменьш", "понизь", "убавь"],
        "de": ["leiser", "verringere", "niedriger", "reduziere"],
        "ar": ["اخفض", "قلل", "أقل"],
    },
    "volume.mute": {
        "en": ["mute"],
        "ru": ["без звука", "выключи звук", "отключи звук"],
        "de": ["stumm", "stummschalten"],
        "ar": ["كتم", "اكتم"],
    },
    "volume.unmute": {
        "en": ["unmute"],
        "ru": ["включи звук", "верни звук"],
        "de": ["stummschaltung aufheben", "ton an"],
        "ar": ["إلغاء الكتم", "أعد الصوت"],
    },
    # --- system: lock screen --------------------------------------------
    "system.lock": {
        "en": ["lock the screen", "lock screen", "lock my pc", "lock computer"],
        "ru": ["заблокируй экран", "блокировка экрана", "заблокируй компьютер", "заблокируй пк"],
        "de": ["bildschirm sperren", "sperre den bildschirm", "computer sperren", "pc sperren"],
        "ar": ["اقفل الشاشة", "قفل الشاشة", "اقفل الكمبيوتر", "قفل الجهاز"],
    },
}


def phrases(intent: str) -> List[str]:
    """Return all trigger phrases for ``intent`` across every language.

    Phrases are returned longest-first so callers that strip a matched prefix
    remove the most specific match (e.g. "search the web for" before "search").
    """
    table = _TRIGGERS.get(intent, {})
    collected: List[str] = []
    for lang_phrases in table.values():
        collected.extend(lang_phrases)
    # Deduplicate while keeping order, then sort longest-first.
    seen, unique = set(), []
    for phrase in collected:
        if phrase not in seen:
            seen.add(phrase)
            unique.append(phrase)
    unique.sort(key=len, reverse=True)
    return unique


def matches_any(text: str, intent: str) -> bool:
    """True if ``text`` contains any trigger phrase for ``intent``."""
    return any(phrase in text for phrase in phrases(intent))


def starts_with_verb(text: str, intent: str = "open.verbs") -> str:
    """If ``text`` starts with an open-verb, return the target; else ``""``.

    Example: ``"öffne notepad"`` -> ``"notepad"``. Matching is whole-word on the
    leading verb so "opener" does not count as "open".
    """
    for verb in phrases(intent):
        if text == verb:
            return ""
        if text.startswith(verb + " "):
            return text[len(verb) + 1:].strip()
    return ""


def strip_trigger(text: str, intent: str) -> str:
    """Remove the first matching trigger phrase and return the remainder.

    Used to extract the payload of a command (the note body, the search query).
    """
    for phrase in phrases(intent):
        if phrase in text:
            return text.split(phrase, 1)[1].strip(" :,.?")
    return text.strip(" :,.?")
