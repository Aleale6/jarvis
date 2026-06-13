"""Take and read back simple notes, persisted to a text file."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .base import Skill, SkillContext

_TRIGGERS = ["take a note", "make a note", "note that", "remember that", "add a note"]
_READ_TRIGGERS = ["read my notes", "read notes", "what are my notes", "list my notes"]


class NotesSkill(Skill):
    name = "notes"
    description = "Save a quick note, or read your notes back."

    def matches(self, text: str) -> bool:
        return self._contains_any(text, _TRIGGERS + _READ_TRIGGERS)

    def run(self, text: str, ctx: SkillContext) -> str:
        notes_path = Path(ctx.config.get("notes_file", "jarvis_notes.txt"))

        if self._contains_any(text, _READ_TRIGGERS):
            return self._read_notes(notes_path)

        note = self._extract_note(text)
        if not note:
            return "What would you like me to note down?"
        return self._save_note(notes_path, note)

    @staticmethod
    def _extract_note(text: str) -> str:
        note = text
        for trigger in _TRIGGERS:
            if trigger in note:
                note = note.split(trigger, 1)[1]
                break
        return note.lstrip(":, ").strip()

    @staticmethod
    def _save_note(path: Path, note: str) -> str:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(f"[{timestamp}] {note}\n")
            return f"Noted: {note}"
        except OSError as exc:
            return f"Sorry, I couldn't save that note ({exc})."

    @staticmethod
    def _read_notes(path: Path) -> str:
        if not path.exists():
            return "You don't have any notes yet."
        try:
            lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        except OSError as exc:
            return f"Sorry, I couldn't read your notes ({exc})."
        if not lines:
            return "You don't have any notes yet."
        recent = lines[-5:]
        return "Here are your latest notes. " + " ... ".join(recent)
