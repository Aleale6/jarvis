"""Structured, line-delimited JSON logging for JARVIS.

Every meaningful action the assistant takes is recorded as one JSON object per
line (JSONL). This format is human-greppable, machine-parseable, and trivial to
ship to a log viewer in the future desktop UI.

Each event captures the fields the master spec calls for:

    timestamp   ISO-8601 UTC time the event was recorded
    level       info | warning | error
    agent       which component emitted it (assistant, safety, router, skill...)
    action      a short verb describing what was requested/done
    result      ok | denied | cancelled | error | <free text>
    error       error message, when applicable
    confirmed   whether the user confirmed a gated action (when applicable)
    detail      arbitrary structured context (never secrets)

The logger never raises: logging must not be able to crash the assistant. If the
log file cannot be written we degrade to stderr and carry on.

Privacy note
------------
The spec requires logging decisions *without exposing internal reasoning*. We
log *what* was decided and *why at a category level* (risk, permission), never
raw model chain-of-thought or API keys. Callers are responsible for not passing
secrets in ``detail``; :func:`_scrub` provides a defensive second line.
"""

from __future__ import annotations

import json
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

#: Keys that must never be written to the log, regardless of caller intent.
_SENSITIVE_KEYS = frozenset(
    {"api_key", "apikey", "authorization", "token", "password", "secret"}
)


def _utc_now_iso() -> str:
    """Return the current UTC time as a stable ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _scrub(detail: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively redact obviously sensitive keys from a detail dict."""
    cleaned: Dict[str, Any] = {}
    for key, value in detail.items():
        if key.lower() in _SENSITIVE_KEYS:
            cleaned[key] = "***redacted***"
        elif isinstance(value, dict):
            cleaned[key] = _scrub(value)
        else:
            cleaned[key] = value
    return cleaned


class EventLogger:
    """Append-only JSONL event logger, safe for concurrent use.

    Parameters
    ----------
    log_path:
        Destination file. Parent directories are created on demand. If ``None``
        or unwritable, events are emitted to stderr instead.
    echo_console:
        When True, a compact human-readable line is also printed to stderr for
        ``warning``/``error`` events (handy during development).
    """

    def __init__(self, log_path: Optional[Path | str] = None, echo_console: bool = False):
        self._lock = threading.Lock()
        self.echo_console = echo_console
        self._path: Optional[Path] = None
        if log_path:
            try:
                path = Path(log_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                self._path = path
            except OSError as exc:  # pragma: no cover - filesystem edge case
                print(f"[logging] Could not prepare log file {log_path}: {exc}", file=sys.stderr)
                self._path = None

    @property
    def path(self) -> Optional[Path]:
        return self._path

    def log(
        self,
        agent: str,
        action: str,
        result: str = "ok",
        *,
        level: str = "info",
        error: Optional[str] = None,
        confirmed: Optional[bool] = None,
        **detail: Any,
    ) -> Dict[str, Any]:
        """Record one structured event and return the event dict.

        Returning the event makes the logger easy to assert on in tests and lets
        callers reuse the same dict for an in-memory activity feed.
        """
        event: Dict[str, Any] = {
            "timestamp": _utc_now_iso(),
            "level": level,
            "agent": agent,
            "action": action,
            "result": result,
        }
        if error is not None:
            event["error"] = error
        if confirmed is not None:
            event["confirmed"] = confirmed
        if detail:
            event["detail"] = _scrub(detail)

        self._write(event)
        return event

    # Convenience wrappers -------------------------------------------------
    def info(self, agent: str, action: str, result: str = "ok", **kw: Any) -> Dict[str, Any]:
        return self.log(agent, action, result, level="info", **kw)

    def warning(self, agent: str, action: str, result: str = "warning", **kw: Any) -> Dict[str, Any]:
        return self.log(agent, action, result, level="warning", **kw)

    def error(self, agent: str, action: str, result: str = "error", **kw: Any) -> Dict[str, Any]:
        return self.log(agent, action, result, level="error", **kw)

    # Internal -------------------------------------------------------------
    def _write(self, event: Dict[str, Any]) -> None:
        line = json.dumps(event, ensure_ascii=False)
        with self._lock:
            if self._path is not None:
                try:
                    with open(self._path, "a", encoding="utf-8") as fh:
                        fh.write(line + "\n")
                except OSError as exc:  # pragma: no cover - filesystem edge case
                    print(f"[logging] Write failed: {exc}", file=sys.stderr)
                    print(line, file=sys.stderr)
            else:
                print(line, file=sys.stderr)

            if self.echo_console and event.get("level") in ("warning", "error"):
                msg = f"[{event['agent']}] {event['action']} -> {event['result']}"
                if event.get("error"):
                    msg += f" ({event['error']})"
                print(msg, file=sys.stderr)


#: Process-wide default logger, lazily created by :func:`get_event_logger`.
_default_logger: Optional[EventLogger] = None


def get_event_logger(
    log_path: Optional[Path | str] = None, echo_console: bool = False
) -> EventLogger:
    """Return the shared :class:`EventLogger`, creating it on first use.

    The first caller decides the destination; later calls return the existing
    instance and ignore their arguments. Pass arguments explicitly when wiring
    the logger at application startup.
    """
    global _default_logger
    if _default_logger is None:
        _default_logger = EventLogger(log_path=log_path, echo_console=echo_console)
    return _default_logger


def reset_event_logger() -> None:
    """Clear the shared logger. Intended for tests only."""
    global _default_logger
    _default_logger = None
