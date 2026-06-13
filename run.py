#!/usr/bin/env python3
"""JARVIS entry point.

Usage:
    python run.py            # voice mode (wake word + microphone)
    python run.py --text     # text mode (type commands; no mic needed)
    python run.py --voices   # list installed TTS voices and exit
"""

from __future__ import annotations

import argparse
import sys

from jarvis.assistant import Assistant
from jarvis.config import Config


def main() -> int:
    parser = argparse.ArgumentParser(description="JARVIS voice assistant")
    parser.add_argument("--text", action="store_true", help="Run in text mode (type commands).")
    parser.add_argument("--voices", action="store_true", help="List installed TTS voices and exit.")
    args = parser.parse_args()

    config = Config.load()

    if args.voices:
        from jarvis.speech.speaker import Speaker

        print("Installed TTS voices (set 'voice.voice_index' in config.json):")
        Speaker(config.section("voice")).list_voices()
        return 0

    assistant = Assistant(config)
    try:
        if args.text:
            assistant.run_text()
        else:
            assistant.run_voice()
    except KeyboardInterrupt:
        print("\nInterrupted. Goodbye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
