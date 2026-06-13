"""Translation tables for JARVIS.

Each supported language maps a stable *message key* to a translated template.
Templates use ``str.format`` style placeholders (e.g. ``{name}``) so the
:class:`~jarvis.i18n.locale.Localizer` can interpolate runtime values.

Supported languages
-------------------
- ``en`` English (default, also the fallback for any missing key)
- ``ru`` Russian (Русский)
- ``de`` German (Deutsch)
- ``ar`` Arabic (العربية) - written right-to-left

Design notes
------------
- English is the canonical key set. Every other language is validated against
  it at import time by :func:`validate_tables`, so a missing or extra key fails
  fast during tests instead of silently degrading at runtime.
- Keys are namespaced with dots (``assistant.online``, ``skill.time.now``) to
  keep the table readable and to group related strings.
"""

from __future__ import annotations

from typing import Dict

# ---------------------------------------------------------------------------
# English - the canonical key set. All other languages must mirror these keys.
# ---------------------------------------------------------------------------
_EN: Dict[str, str] = {
    # Assistant lifecycle
    "assistant.online_voice": "{name} online. Say '{wake_word}' followed by a command.",
    "assistant.online_text": "{name} online in text mode. Type a command, or '{quit}' to stop.",
    "assistant.no_mic": "I can't access a microphone, so I'll switch to text mode. Type your commands instead.",
    "assistant.powering_down": "Powering down. Goodbye.",
    "assistant.goodbye": "Goodbye.",
    "assistant.yes": "Yes?",
    "assistant.not_understood": "I didn't catch that.",
    "assistant.skill_error": "Sorry, something went wrong running that.",
    "assistant.no_llm": (
        "I can't answer open questions yet because no language model is "
        "configured. But I can tell the time, open apps, search the web, take "
        "notes, and control the volume."
    ),
    "assistant.llm_unsure": "I'm not sure how to answer that.",
    "assistant.help_prefix": "I can ",
    "assistant.help_join": ", ",
    # Help ability descriptions
    "help.time": "tell the time and date",
    "help.apps": "open applications like notepad or chrome",
    "help.web": "search the web and open websites",
    "help.notes": "take and read notes",
    "help.system": "control the volume and lock the screen",
    "help.general": "answer general questions",
    # Safety / confirmation pipeline
    "safety.confirm": "This will {action}. Should I go ahead? Say yes to confirm.",
    "safety.confirmed": "Confirmed.",
    "safety.cancelled": "Okay, I won't do that.",
    "safety.denied": "That action isn't permitted by your current settings.",
    "safety.affirmatives": "yes|yeah|yep|sure|go ahead|do it|confirm|okay|ok|proceed",
    # Time / date skill
    "skill.time.now": "It's {time}.",
    "skill.time.today": "Today is {date}.",
    # System control skill
    "skill.system.opening": "Opening {app}.",
    "skill.system.open_failed": "Sorry, I couldn't open {app} ({error}).",
    "skill.system.which_app": "Which application should I open?",
    "skill.system.unsure_open": "I'm not sure what to open.",
    "skill.system.muted": "Muted.",
    "skill.system.unmuted": "Unmuted.",
    "skill.system.volume_up": "Turning the volume up.",
    "skill.system.volume_down": "Turning the volume down.",
    "skill.system.volume_help": "Say volume up, volume down, or mute.",
    "skill.system.volume_win_only": "Volume control is only wired up for Windows right now.",
    "skill.system.locking": "Locking the screen.",
    "skill.system.lock_failed": "Sorry, I couldn't lock the screen.",
    "skill.system.lock_win_only": "Locking the screen is only supported on Windows here.",
    "skill.system.action_open": "open {app}",
    "skill.system.action_lock": "lock your screen",
    # Notes skill
    "skill.notes.noted": "Noted: {note}",
    "skill.notes.what": "What would you like me to note down?",
    "skill.notes.save_failed": "Sorry, I couldn't save that note ({error}).",
    "skill.notes.read_failed": "Sorry, I couldn't read your notes ({error}).",
    "skill.notes.none": "You don't have any notes yet.",
    "skill.notes.latest": "Here are your latest notes. {notes}",
    # Web skill
    "skill.web.opening": "Opening {target}.",
    "skill.web.searching": "Searching the web for {query}.",
    "skill.web.what": "What would you like me to search for?",
    # LLM language steering (appended to the system prompt)
    "llm.language_directive": "Always reply in English, regardless of the language of the question.",
    # Spoken phrases that end the session
    "exit.phrases": "goodbye|shut down|power down|exit|quit",
}

# ---------------------------------------------------------------------------
# Russian
# ---------------------------------------------------------------------------
_RU: Dict[str, str] = {
    "assistant.online_voice": "{name} в сети. Скажите «{wake_word}» и затем команду.",
    "assistant.online_text": "{name} в сети в текстовом режиме. Введите команду или «{quit}», чтобы выйти.",
    "assistant.no_mic": "Не удаётся получить доступ к микрофону, переключаюсь в текстовый режим. Вводите команды.",
    "assistant.powering_down": "Завершаю работу. До свидания.",
    "assistant.goodbye": "До свидания.",
    "assistant.yes": "Да?",
    "assistant.not_understood": "Я не расслышал.",
    "assistant.skill_error": "Извините, при выполнении произошла ошибка.",
    "assistant.no_llm": (
        "Пока я не могу отвечать на свободные вопросы, потому что языковая модель "
        "не настроена. Но я могу подсказать время, открыть приложения, искать в "
        "интернете, делать заметки и управлять громкостью."
    ),
    "assistant.llm_unsure": "Я не уверен, как на это ответить.",
    "assistant.help_prefix": "Я могу ",
    "assistant.help_join": ", ",
    "help.time": "сказать время и дату",
    "help.apps": "открывать приложения, например блокнот или Chrome",
    "help.web": "искать в интернете и открывать сайты",
    "help.notes": "делать и читать заметки",
    "help.system": "управлять громкостью и блокировать экран",
    "help.general": "отвечать на общие вопросы",
    "safety.confirm": "Это действие: {action}. Продолжить? Скажите «да» для подтверждения.",
    "safety.confirmed": "Подтверждено.",
    "safety.cancelled": "Хорошо, я не буду этого делать.",
    "safety.denied": "Это действие запрещено вашими текущими настройками.",
    "safety.affirmatives": "да|давай|конечно|подтверждаю|вперёд|ок|окей|хорошо|продолжай",
    "skill.time.now": "Сейчас {time}.",
    "skill.time.today": "Сегодня {date}.",
    "skill.system.opening": "Открываю {app}.",
    "skill.system.open_failed": "Извините, не удалось открыть {app} ({error}).",
    "skill.system.which_app": "Какое приложение открыть?",
    "skill.system.unsure_open": "Я не понял, что открыть.",
    "skill.system.muted": "Звук выключен.",
    "skill.system.unmuted": "Звук включён.",
    "skill.system.volume_up": "Увеличиваю громкость.",
    "skill.system.volume_down": "Уменьшаю громкость.",
    "skill.system.volume_help": "Скажите «громче», «тише» или «без звука».",
    "skill.system.volume_win_only": "Управление громкостью пока работает только в Windows.",
    "skill.system.locking": "Блокирую экран.",
    "skill.system.lock_failed": "Извините, не удалось заблокировать экран.",
    "skill.system.lock_win_only": "Блокировка экрана здесь поддерживается только в Windows.",
    "skill.system.action_open": "открыть {app}",
    "skill.system.action_lock": "заблокировать экран",
    "skill.notes.noted": "Записал: {note}",
    "skill.notes.what": "Что записать?",
    "skill.notes.save_failed": "Извините, не удалось сохранить заметку ({error}).",
    "skill.notes.read_failed": "Извините, не удалось прочитать заметки ({error}).",
    "skill.notes.none": "У вас пока нет заметок.",
    "skill.notes.latest": "Вот ваши последние заметки. {notes}",
    "skill.web.opening": "Открываю {target}.",
    "skill.web.searching": "Ищу в интернете: {query}.",
    "skill.web.what": "Что мне найти?",
    "llm.language_directive": "Всегда отвечай на русском языке, независимо от языка вопроса.",
    "exit.phrases": "до свидания|выключись|отключись|выход|стоп|пока",
}

# ---------------------------------------------------------------------------
# German
# ---------------------------------------------------------------------------
_DE: Dict[str, str] = {
    "assistant.online_voice": "{name} ist online. Sagen Sie «{wake_word}» gefolgt von einem Befehl.",
    "assistant.online_text": "{name} ist im Textmodus online. Geben Sie einen Befehl ein oder «{quit}» zum Beenden.",
    "assistant.no_mic": "Ich kann nicht auf ein Mikrofon zugreifen und wechsle in den Textmodus. Bitte tippen Sie Ihre Befehle.",
    "assistant.powering_down": "Fahre herunter. Auf Wiedersehen.",
    "assistant.goodbye": "Auf Wiedersehen.",
    "assistant.yes": "Ja?",
    "assistant.not_understood": "Das habe ich nicht verstanden.",
    "assistant.skill_error": "Entschuldigung, dabei ist etwas schiefgelaufen.",
    "assistant.no_llm": (
        "Ich kann offene Fragen noch nicht beantworten, weil kein Sprachmodell "
        "konfiguriert ist. Aber ich kann die Uhrzeit nennen, Apps öffnen, im Web "
        "suchen, Notizen machen und die Lautstärke steuern."
    ),
    "assistant.llm_unsure": "Ich bin mir nicht sicher, wie ich das beantworten soll.",
    "assistant.help_prefix": "Ich kann ",
    "assistant.help_join": ", ",
    "help.time": "die Uhrzeit und das Datum nennen",
    "help.apps": "Anwendungen wie Editor oder Chrome öffnen",
    "help.web": "im Web suchen und Webseiten öffnen",
    "help.notes": "Notizen machen und vorlesen",
    "help.system": "die Lautstärke steuern und den Bildschirm sperren",
    "help.general": "allgemeine Fragen beantworten",
    "safety.confirm": "Dadurch wird Folgendes geschehen: {action}. Soll ich fortfahren? Sagen Sie ja zur Bestätigung.",
    "safety.confirmed": "Bestätigt.",
    "safety.cancelled": "In Ordnung, ich mache das nicht.",
    "safety.denied": "Diese Aktion ist mit Ihren aktuellen Einstellungen nicht erlaubt.",
    "safety.affirmatives": "ja|jawohl|klar|sicher|mach es|bestätigen|okay|ok|fortfahren",
    "skill.time.now": "Es ist {time}.",
    "skill.time.today": "Heute ist {date}.",
    "skill.system.opening": "Öffne {app}.",
    "skill.system.open_failed": "Entschuldigung, ich konnte {app} nicht öffnen ({error}).",
    "skill.system.which_app": "Welche Anwendung soll ich öffnen?",
    "skill.system.unsure_open": "Ich bin mir nicht sicher, was ich öffnen soll.",
    "skill.system.muted": "Stummgeschaltet.",
    "skill.system.unmuted": "Stummschaltung aufgehoben.",
    "skill.system.volume_up": "Erhöhe die Lautstärke.",
    "skill.system.volume_down": "Verringere die Lautstärke.",
    "skill.system.volume_help": "Sagen Sie lauter, leiser oder stumm.",
    "skill.system.volume_win_only": "Die Lautstärkeregelung funktioniert derzeit nur unter Windows.",
    "skill.system.locking": "Sperre den Bildschirm.",
    "skill.system.lock_failed": "Entschuldigung, ich konnte den Bildschirm nicht sperren.",
    "skill.system.lock_win_only": "Das Sperren des Bildschirms wird hier nur unter Windows unterstützt.",
    "skill.system.action_open": "{app} öffnen",
    "skill.system.action_lock": "Ihren Bildschirm sperren",
    "skill.notes.noted": "Notiert: {note}",
    "skill.notes.what": "Was soll ich notieren?",
    "skill.notes.save_failed": "Entschuldigung, ich konnte die Notiz nicht speichern ({error}).",
    "skill.notes.read_failed": "Entschuldigung, ich konnte Ihre Notizen nicht lesen ({error}).",
    "skill.notes.none": "Sie haben noch keine Notizen.",
    "skill.notes.latest": "Hier sind Ihre neuesten Notizen. {notes}",
    "skill.web.opening": "Öffne {target}.",
    "skill.web.searching": "Suche im Web nach {query}.",
    "skill.web.what": "Wonach soll ich suchen?",
    "llm.language_directive": "Antworte immer auf Deutsch, unabhängig von der Sprache der Frage.",
    "exit.phrases": "auf wiedersehen|herunterfahren|ausschalten|beenden|tschüss|stopp",
}

# ---------------------------------------------------------------------------
# Arabic (right-to-left)
# ---------------------------------------------------------------------------
_AR: Dict[str, str] = {
    "assistant.online_voice": "{name} متصل. قل «{wake_word}» متبوعًا بأمر.",
    "assistant.online_text": "{name} متصل في الوضع النصي. اكتب أمرًا أو «{quit}» للإيقاف.",
    "assistant.no_mic": "لا أستطيع الوصول إلى الميكروفون، لذا سأنتقل إلى الوضع النصي. اكتب أوامرك.",
    "assistant.powering_down": "جارٍ إيقاف التشغيل. إلى اللقاء.",
    "assistant.goodbye": "إلى اللقاء.",
    "assistant.yes": "نعم؟",
    "assistant.not_understood": "لم أسمع ذلك جيدًا.",
    "assistant.skill_error": "عذرًا، حدث خطأ أثناء تنفيذ ذلك.",
    "assistant.no_llm": (
        "لا أستطيع الإجابة عن الأسئلة المفتوحة بعد لأنه لم يتم إعداد نموذج لغوي. "
        "لكن يمكنني إخبارك بالوقت وفتح التطبيقات والبحث في الويب وتدوين الملاحظات "
        "والتحكم في مستوى الصوت."
    ),
    "assistant.llm_unsure": "لست متأكدًا من كيفية الإجابة عن ذلك.",
    "assistant.help_prefix": "يمكنني ",
    "assistant.help_join": "، ",
    "help.time": "إخبارك بالوقت والتاريخ",
    "help.apps": "فتح تطبيقات مثل المفكرة أو كروم",
    "help.web": "البحث في الويب وفتح المواقع",
    "help.notes": "تدوين الملاحظات وقراءتها",
    "help.system": "التحكم في مستوى الصوت وقفل الشاشة",
    "help.general": "الإجابة عن الأسئلة العامة",
    "safety.confirm": "سيؤدي هذا إلى: {action}. هل أتابع؟ قل نعم للتأكيد.",
    "safety.confirmed": "تم التأكيد.",
    "safety.cancelled": "حسنًا، لن أفعل ذلك.",
    "safety.denied": "هذا الإجراء غير مسموح به وفقًا لإعداداتك الحالية.",
    "safety.affirmatives": "نعم|أجل|تمام|أكيد|تابع|أكد|حسنا|موافق|هيا",
    "skill.time.now": "الساعة الآن {time}.",
    "skill.time.today": "اليوم هو {date}.",
    "skill.system.opening": "جارٍ فتح {app}.",
    "skill.system.open_failed": "عذرًا، لم أتمكن من فتح {app} ({error}).",
    "skill.system.which_app": "أي تطبيق تريد أن أفتح؟",
    "skill.system.unsure_open": "لست متأكدًا مما يجب فتحه.",
    "skill.system.muted": "تم كتم الصوت.",
    "skill.system.unmuted": "تم إلغاء كتم الصوت.",
    "skill.system.volume_up": "جارٍ رفع مستوى الصوت.",
    "skill.system.volume_down": "جارٍ خفض مستوى الصوت.",
    "skill.system.volume_help": "قل ارفع الصوت أو اخفض الصوت أو كتم.",
    "skill.system.volume_win_only": "التحكم في مستوى الصوت متاح حاليًا على ويندوز فقط.",
    "skill.system.locking": "جارٍ قفل الشاشة.",
    "skill.system.lock_failed": "عذرًا، لم أتمكن من قفل الشاشة.",
    "skill.system.lock_win_only": "قفل الشاشة مدعوم هنا على ويندوز فقط.",
    "skill.system.action_open": "فتح {app}",
    "skill.system.action_lock": "قفل شاشتك",
    "skill.notes.noted": "تم التدوين: {note}",
    "skill.notes.what": "ماذا تريد أن أدوّن؟",
    "skill.notes.save_failed": "عذرًا، لم أتمكن من حفظ الملاحظة ({error}).",
    "skill.notes.read_failed": "عذرًا، لم أتمكن من قراءة ملاحظاتك ({error}).",
    "skill.notes.none": "ليس لديك أي ملاحظات بعد.",
    "skill.notes.latest": "إليك أحدث ملاحظاتك. {notes}",
    "skill.web.opening": "جارٍ فتح {target}.",
    "skill.web.searching": "أبحث في الويب عن {query}.",
    "skill.web.what": "عمّ تريد أن أبحث؟",
    "llm.language_directive": "أجب دائمًا باللغة العربية بغض النظر عن لغة السؤال.",
    "exit.phrases": "إلى اللقاء|أوقف التشغيل|اخرج|توقف|وداعا",
}


#: Master registry: language code -> translation table.
TABLES: Dict[str, Dict[str, str]] = {
    "en": _EN,
    "ru": _RU,
    "de": _DE,
    "ar": _AR,
}

#: Languages whose script is written right-to-left.
RTL_LANGUAGES = frozenset({"ar"})

#: The canonical language whose keys every other table must mirror.
DEFAULT_LANGUAGE = "en"


def validate_tables() -> None:
    """Ensure every language defines exactly the canonical (English) key set.

    Raises
    ------
    ValueError
        If any language table is missing keys present in English or defines
        extra keys that English does not. Called at import time so packaging or
        translation mistakes surface immediately rather than at runtime.
    """
    canonical = set(TABLES[DEFAULT_LANGUAGE].keys())
    problems = []
    for lang, table in TABLES.items():
        if lang == DEFAULT_LANGUAGE:
            continue
        keys = set(table.keys())
        missing = canonical - keys
        extra = keys - canonical
        if missing:
            problems.append(f"[{lang}] missing keys: {sorted(missing)}")
        if extra:
            problems.append(f"[{lang}] unexpected keys: {sorted(extra)}")
    if problems:
        raise ValueError("Translation table mismatch:\n" + "\n".join(problems))


# Fail fast on import if the tables drift out of sync.
validate_tables()
