"""Take and read back simple notes, persisted to a text file (multilingual)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..i18n.triggers import matches_any, strip_trigger
from .base import Skill, SkillContext


class NotesSkill(Skill):
    name = "notes"
    description = "Save a quick note, or read your notes back."

    def matches(self, text: str) -> bool:
        return matches_any(text, "notes.take") or matches_any(text, "notes.read")

    def run(self, text: str, ctx: SkillContext) -> str:
        notes_path = Path(ctx.config.get("notes_file", "jarvis_notes.txt"))

        # Read takes precedence so "read my notes" isn't mistaken for "note".
        if matches_any(text, "notes.read"):
            return self._read_notes(notes_path, ctx)

        note = strip_trigger(text, "notes.take")
        if not note:
            return ctx.t("skill.notes.what")
        return self._save_note(notes_path, note, ctx)

    @staticmethod
    def _save_note(path: Path, note: str, ctx: SkillContext) -> str:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(f"[{timestamp}] {note}\n")
            ctx.logger.info(agent="notes", action="save_note", result="ok")
            return ctx.t("skill.notes.noted", note=note)
        except OSError as exc:
            ctx.logger.error(agent="notes", action="save_note", error=str(exc))
            return ctx.t("skill.notes.save_failed", error=exc)

    @staticmethod
    def _read_notes(path: Path, ctx: SkillContext) -> str:
        if not path.exists():
            return ctx.t("skill.notes.none")
        try:
            lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        except OSError as exc:
            ctx.logger.error(agent="notes", action="read_notes", error=str(exc))
            return ctx.t("skill.notes.read_failed", error=exc)
        if not lines:
            return ctx.t("skill.notes.none")
        recent = lines[-5:]
        return ctx.t("skill.notes.latest", notes=" ... ".join(recent))
