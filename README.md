# JARVIS — A Voice Assistant for Windows 10

A modular, voice-activated AI assistant inspired by Iron Man's JARVIS. It listens
for a wake word, transcribes your speech, answers questions using an LLM, talks
back with a synthesized voice, and can perform real actions on your PC (open apps,
search the web, tell the time, take notes, control volume, and more).

```
  You: "Jarvis, what time is it?"
  JARVIS (speaks): "It's 4:32 PM."

  You: "Jarvis, open notepad."
  JARVIS (speaks): "Opening notepad."

  You: "Jarvis, who painted the Mona Lisa?"
  JARVIS (speaks): "Leonardo da Vinci painted the Mona Lisa."
```

## Features

- 🎙️ **Wake-word listening** — say "Jarvis ..." to give a command.
- 🗣️ **Speech-to-text** — via Google's free recognizer (needs internet).
- 🔊 **Text-to-speech** — fully offline using Windows SAPI5 voices.
- 🧠 **LLM brain** — answers open-ended questions (OpenAI-compatible API).
- ⚙️ **Skills** — open apps, web search, time/date, notes, volume control, exit.
- 🧩 **Modular** — add your own skills by dropping in a small class.

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

You'll hear a greeting. Then just say **"Jarvis"** followed by your request, e.g.:

- "Jarvis, what time is it?"
- "Jarvis, open calculator."
- "Jarvis, search the web for the weather in Seattle."
- "Jarvis, take a note: buy groceries tomorrow."
- "Jarvis, volume up."
- "Jarvis, tell me a joke." (uses the LLM)
- "Jarvis, goodbye." (shuts down)

You can also run in **text mode** (type instead of speak) for testing without a mic:

```bat
python run.py --text
```

## Project structure

```
jarvis/
├── run.py                 # Entry point
├── requirements.txt
├── config.example.json    # Copy to config.json
├── README.md
└── jarvis/
    ├── __init__.py
    ├── config.py          # Loads config.json + env vars
    ├── assistant.py       # Orchestrates listen -> route -> respond
    ├── speech/
    │   ├── __init__.py
    │   ├── speaker.py      # Text-to-speech (pyttsx3)
    │   └── listener.py     # Speech-to-text + wake word (SpeechRecognition)
    ├── brain/
    │   ├── __init__.py
    │   └── llm.py          # OpenAI-compatible chat client + memory
    └── skills/
        ├── __init__.py
        ├── base.py         # Skill base class + registry
        ├── time_date.py
        ├── system_control.py
        ├── web.py
        └── notes.py
```

## Adding your own skill

Create a class that subclasses `Skill`, implement `matches()` and `run()`, and
register it. See `jarvis/skills/time_date.py` for the simplest example.

## Notes & limitations

- Speech recognition uses Google's free web API (needs internet). For a fully
  offline recognizer you can swap in [Vosk](https://alphacephei.com/vosk/).
- This is a real, practical assistant — not the movie's sentient AI. Treat it as
  a strong, extensible voice front-end to your PC and an LLM.
