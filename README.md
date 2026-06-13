# JARVIS — A Multilingual Voice Assistant for Windows 10

A modular, voice-activated AI assistant inspired by Iron Man's JARVIS. It listens
for a wake word, transcribes your speech, answers questions using a language
model, talks back with a synthesized voice, and can perform real actions on your
PC (open apps, search the web, tell the time, take notes, control volume, and
more). It speaks **English, Russian, German, and Arabic**, routes requests across
**multiple AI providers**, and gates every system-affecting action through a
**safety/confirmation pipeline** with a structured audit log.

```
  You: "Jarvis, what time is it?"
  JARVIS (speaks): "It's 4:32 PM."

  Вы: «Джарвис, открой блокнот.»
  JARVIS (говорит): «Открываю блокнот.»

  Sie: „Jarvis, wie spät ist es?"
  JARVIS (spricht): „Es ist 16:32 Uhr."

  أنت: «جارفِس، كم الساعة؟»
  JARVIS (يتحدث): «الساعة الآن 4:32 مساءً.»
```

## Features

- **Multilingual** — English, Russian, German, Arabic. Replies, skill triggers,
  the LLM, the speech recognizer locale, and the TTS voice all follow the active
  language, which can be set in config or auto-detected per utterance.
- **Wake-word listening** — say "Jarvis ..." to give a command.
- **Speech-to-text** — via Google's free recognizer (needs internet), per-language.
- **Text-to-speech** — offline Windows SAPI5 voices, auto-matched to the language.
- **Multi-provider AI brain** — OpenAI, Anthropic (Claude), Google Gemini, and
  local OpenAI-compatible servers (Ollama / LM Studio). The router picks a backend
  by task (reasoning / coding / chat), privacy, language, and availability, and
  falls back automatically when one fails.
- **Safety & permissions** — every system action is risk-assessed; medium/high
  risk or irreversible actions ask for confirmation unless you pre-authorize the
  category. Categories can also be blocked outright.
- **Structured logging** — every decision and action is recorded as JSON Lines.
- **Skills** — open apps, web search, time/date, notes, volume control, lock.
- **Modular** — add your own skills and AI providers without touching the core.

## Architecture

```
                 ┌──────────────────────────────────────────────┐
   mic / text ──▶│  Assistant (orchestrator)                     │
                 │   • Localizer (en/ru/de/ar)                    │
                 │   • language auto-detect & switch             │
                 │   • confirmation prompt                       │
                 └───┬───────────────┬───────────────┬───────────┘
                     │               │               │
              ┌──────▼─────┐   ┌─────▼──────┐   ┌─────▼───────┐
              │  Skills    │   │  Safety    │   │  LLM Brain  │
              │ time/web/  │──▶│  Manager   │   │  + Router   │
              │ notes/sys  │   │ (risk +    │   │  ┌────────┐ │
              └────────────┘   │  permits)  │   │  │OpenAI  │ │
                     │         └─────┬──────┘   │  │Anthropic│ │
                     │               │          │  │Gemini  │ │
                     ▼               ▼          │  │Local   │ │
              ┌─────────────────────────────┐  │  └────────┘ │
              │  EventLogger (JSONL audit)   │  └─────────────┘
              └─────────────────────────────┘
```

## Requirements

- Windows 10
- Python 3.9+  (https://www.python.org/downloads/ — check "Add Python to PATH")
- A working microphone and speakers
- (Optional) An API key for an OpenAI-compatible LLM, to enable open conversation

## Setup

```bat
:: 1. From the jarvis\ folder, create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate

:: 2. Install dependencies
pip install -r requirements.txt

:: If PyAudio fails to install, use pipwin:
::   pip install pipwin
::   pipwin install pyaudio

:: 3. Create your config from the example
copy config.example.json config.json
```

Then open `config.json` and (optionally) paste your LLM API key into `llm.api_key`.
You can also set it via an environment variable instead (recommended):

```bat
setx JARVIS_API_KEY "sk-your-key-here"
```

> No API key? JARVIS still runs — the built-in skills (time, open apps, web
> search, notes, volume) all work offline. Only open-ended conversation needs
> the LLM.

## Run

```bat
.venv\Scripts\activate
python run.py
```

You'll hear a greeting. Then just say **"Jarvis"** followed by your request. The
same commands work in every supported language:

| Intent | English | Russian | German | Arabic |
|--------|---------|---------|--------|--------|
| Time | "what time is it" | "который час" | "wie spät ist es" | "كم الساعة" |
| Open app | "open calculator" | "открой калькулятор" | "öffne paint" | "افتح المفكرة" |
| Web search | "search for weather" | "найди погоду" | "suche nach wetter" | "ابحث عن الطقس" |
| Take note | "take a note ..." | "запиши ..." | "notiere ..." | "دوّن ملاحظة ..." |
| Volume | "volume up" | "громче" | "lauter" | "ارفع الصوت" |
| Lock | "lock the screen" | "заблокируй экран" | "bildschirm sperren" | "اقفل الشاشة" |
| Quit | "goodbye" | "пока" | "tschüss" | "إلى اللقاء" |

You can also run in **text mode** (type instead of speak) for testing without a mic:

```bat
python run.py --text
```

## Languages

Set the default language in `config.json` (`"language": "en" | "ru" | "de" | "ar"`)
or via the `JARVIS_LANGUAGE` environment variable. With `"auto_detect_language":
true` (the default), JARVIS detects the language of each command and switches the
replies, the recognition locale, and the speech voice to match. For the best
spoken experience, install the matching Windows SAPI5 voice (e.g. a Russian or
German voice) — JARVIS will pick it automatically.

## Configuration

`config.json` is created from `config.example.json`. Key sections:

- **`llm.providers`** — an ordered list of AI backends. Each entry has a `type`
  (`openai`, `anthropic`, `gemini`, or `local`), a `model`, an `api_key`, an
  optional `base_url`, a `priority` (lower = preferred), and `capabilities`
  (`reasoning`, `coding`, `context_tokens`, `local`). The router scores them per
  request and falls back on failure. Set `llm.private: true` to force local-only
  models. A legacy flat config (single `base_url`/`api_key`/`model`) still works.
- **`safety`** — `granted_permissions` (categories allowed without a prompt),
  `blocked_permissions` (always denied), `confirm_medium_risk` (ask before
  medium-risk actions), and `auto_confirm` (for unattended/testing use).
  Permission categories: `app_control`, `system_settings`, `file_read`,
  `file_write`, `shell`, `web`, `network`.
- **`logging`** — `file` (JSONL audit log path; set to `null` for stderr) and
  `echo_console`.

## Testing

```bat
pip install -r requirements-dev.txt
pytest
```

The suite (67 tests) covers localization, triggers, the safety pipeline, logging,
provider routing/fallback, and end-to-end assistant behaviour in all four
languages — and runs fully offline (no network, no microphone).

## Project structure

```
jarvis/
├── run.py                 # Entry point
├── requirements.txt
├── requirements-dev.txt
├── config.example.json    # Copy to config.json
├── README.md
├── tests/                 # pytest suite (offline)
└── jarvis/
    ├── __init__.py
    ├── config.py          # Loads config.json + env vars
    ├── assistant.py       # Orchestrates listen -> understand -> gate -> respond
    ├── i18n/
    │   ├── locale.py       # Localizer: language, STT locale, TTS hints, detect
    │   ├── strings.py      # Translation tables (en/ru/de/ar)
    │   └── triggers.py     # Multilingual command triggers
    ├── core/
    │   ├── logging_setup.py# Structured JSONL event logger
    │   └── safety.py       # Risk assessment + permission/confirm pipeline
    ├── speech/
    │   ├── speaker.py      # Language-aware text-to-speech (pyttsx3)
    │   └── listener.py     # Speech-to-text + wake word (SpeechRecognition)
    ├── brain/
    │   ├── llm.py          # LLM brain (uses the router + language steering)
    │   ├── router.py       # Multi-provider router with capability fallback
    │   └── providers/      # openai / anthropic / gemini / local + factory
    └── skills/
        ├── base.py         # Skill base class, SkillContext, registry
        ├── time_date.py
        ├── system_control.py
        ├── web.py
        └── notes.py
```

## Adding your own skill

Create a class that subclasses `Skill`, implement `matches()` and `run(text, ctx)`,
and register it in `jarvis/skills/base.py`. Use `ctx.t("key")` for localized
replies, add triggers to `jarvis/i18n/triggers.py`, and gate any system-affecting
action with `ctx.safety.gate(SafetyRequest(...), confirm=ctx.confirm)`. See
`time_date.py` (simplest) and `system_control.py` (safety-gated) for examples.

## Adding your own AI provider

Subclass `BaseProvider`, implement `_complete(...)`, and register it with
`register_provider("mykind", MyProvider)`. It then becomes selectable from
`llm.providers` config like any built-in backend.

## Roadmap

This codebase is the local-first core. The larger JARVIS vision is built on top
incrementally, without redesign:

- **Memory subsystem** — SQLite + a vector store for long-term/semantic memory,
  user preferences, and project memory, with user-controlled editing/deletion.
- **Desktop UI** — a Tauri/React dark-mode dashboard (conversation, agent
  activity, resource monitor, memory explorer, plugin manager, log viewer).
- **Multi-agent orchestration** — promote skills into specialized agents
  (executive, coding, research, file, browser, vision) communicating via
  structured messages, building on the existing safety + logging spine.
- **More integrations** — vision/document/PDF analysis, file-management and
  browser-automation skills, and a plugin SDK with scoped permissions.

## Notes & limitations

- Speech recognition uses Google's free web API (needs internet). For a fully
  offline recognizer you can swap in [Vosk](https://alphacephei.com/vosk/), which
  also has Russian, German, and Arabic models.
- System actions (open app, volume, lock) target Windows; on other OSes they
  report that politely. The language, safety, logging, and routing layers are
  cross-platform.
- This is a real, practical assistant — not the movie's sentient AI. Treat it as
  a strong, extensible, multilingual voice front-end to your PC and an LLM.
